"""Implémentation PostgreSQL des ports ProductRepository et OrderRepository."""
from collections.abc import Mapping, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.adapters.outbound.persistence.orm import OrderItemRow, OrderRow, ProductRow
from app.domain.order import Order, OrderLine, OrderStatus
from app.domain.product import Product
from app.domain.value_objects import Money, Quantity


# ----- Traduction ligne SQL  ->  objet du domaine -----
def _product_to_domain(row: ProductRow) -> Product:
    return Product(id=row.id, name=row.name, unit_price=Money(row.unit_price), stock=row.stock)


def _order_to_domain(row: OrderRow) -> Order:
    return Order(
        id=row.id,
        created_at=row.created_at,
        status=OrderStatus(row.status),
        lines=[
            OrderLine(
                product_id=i.product_id,
                product_name=i.product_name,
                quantity=Quantity(i.quantity),
                unit_price=Money(i.unit_price),
            )
            for i in row.items
        ],
    )


class SqlAlchemyProductRepository:
    def __init__(self, session: Session):
        self._session = session

    def list_all(self) -> list[Product]:
        rows = self._session.scalars(select(ProductRow).order_by(ProductRow.id))
        return [_product_to_domain(r) for r in rows]

    def get_many_for_update(self, product_ids: Sequence[int]) -> Mapping[int, Product]:
        rows = self._session.scalars(
            select(ProductRow)
            .where(ProductRow.id.in_(product_ids))
            .order_by(ProductRow.id)  # ordre fixe : deux transactions ne se bloquent pas mutuellement
            .with_for_update()
        )
        return {r.id: _product_to_domain(r) for r in rows}

    def save(self, product: Product) -> None:
        row = self._session.get(ProductRow, product.id)
        row.stock = product.stock


class SqlAlchemyOrderRepository:
    def __init__(self, session: Session):
        self._session = session

    def add(self, order: Order) -> None:
        row = OrderRow(
            created_at=order.created_at,
            total_amount=order.total.amount,
            status=order.status.value,
            items=[
                OrderItemRow(
                    product_id=line.product_id,
                    product_name=line.product_name,
                    quantity=line.quantity.value,
                    unit_price=line.unit_price.amount,
                )
                for line in order.lines
            ],
        )
        self._session.add(row)
        self._session.flush()  # obtient l'id généré par PostgreSQL
        order.id = row.id

    def _select(self):
        return select(OrderRow).options(selectinload(OrderRow.items))

    def get(self, order_id: int) -> Order | None:
        row = self._session.scalars(self._select().where(OrderRow.id == order_id)).one_or_none()
        return _order_to_domain(row) if row else None

    def get_for_update(self, order_id: int) -> Order | None:
        row = self._session.scalars(
            self._select().where(OrderRow.id == order_id).with_for_update()
        ).one_or_none()
        return _order_to_domain(row) if row else None

    def list(self, status: OrderStatus | None = None) -> list[Order]:
        stmt = self._select().order_by(OrderRow.created_at.desc(), OrderRow.id.desc())
        if status:
            stmt = stmt.where(OrderRow.status == status.value)
        return [_order_to_domain(r) for r in self._session.scalars(stmt)]

    def save(self, order: Order) -> None:
        # Seul le statut peut changer après création (les lignes sont figées).
        row = self._session.get(OrderRow, order.id)
        row.status = order.status.value
