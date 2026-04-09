"""Basic local CLI consumer for the application layer."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sqlite3
import sys
from typing import TextIO

from Modules.app.application_service import (
    AddBasketItemUseCase,
    ApplicationService,
    ClearBasketUseCase,
    CompareBasketUseCase,
    GetBasketStateUseCase,
    ListChainsUseCase,
    LoadPricesUseCase,
    RemoveBasketItemUseCase,
    UpdateBasketItemQuantityUseCase,
)
from Modules.data.data_loader import PriceDataLoader
from Modules.db.database import ConnectionFactory, create_schema
from Modules.db.repositories import BasketRepository
from Modules.engine.basket_engine import BasketEngine
from Modules.models.entities import BasketItem
from Modules.models.results import BasketComparisonResult, MatchStatus
from Modules.utils.text_utils import normalize_product_name


@dataclass(slots=True)
class CliLoadRequest:
    """CLI load request used by the application use case."""

    entity: str
    source_path: str
    mode: str


class CliLoadDispatcher:
    """Thin adapter that maps CLI load requests to loader operations."""

    def __init__(self, data_loader: PriceDataLoader) -> None:
        self._data_loader = data_loader

    def load_prices(self, load_request: CliLoadRequest) -> object:
        if load_request.entity == "products":
            return self._data_loader.load_products(load_request.source_path, load_request.mode)
        if load_request.entity == "stores":
            return self._data_loader.load_stores(load_request.source_path, load_request.mode)
        if load_request.entity == "prices":
            return self._data_loader.load_prices(load_request.source_path, load_request.mode)
        raise ValueError(f"unsupported entity: {load_request.entity}")


class SqliteChainReadRepository:
    """Read model for chain listing."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def list_chains(self) -> list[dict[str, object]]:
        rows = self._connection.execute(
            "SELECT id, name FROM chains ORDER BY id"
        ).fetchall()
        return [{"id": int(row[0]), "name": str(row[1])} for row in rows]


class SqliteBasketComparisonService:
    """SQLite-backed comparison service used by the app-layer use case."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._engine = BasketEngine()

    def compare_basket(self, basket_items: list[BasketItem]) -> BasketComparisonResult:
        unmatched_items: list[str] = []
        matched_items: list[BasketItem] = []

        for item in basket_items:
            if item.match_status == MatchStatus.MATCHED.value and item.product_id is not None:
                matched_items.append(item)
            else:
                unmatched_items.append(item.input_value)

        if not matched_items:
            return BasketComparisonResult(ranked_chains=[], unmatched_items=unmatched_items)

        product_lookup = self._load_products([item.product_id for item in matched_items if item.product_id is not None])
        price_lookup = self._load_chain_min_prices(product_lookup.keys())
        chain_rows = self._connection.execute(
            "SELECT id, name FROM chains ORDER BY id"
        ).fetchall()

        chain_inputs: list[dict[str, object]] = []
        for chain_row in chain_rows:
            chain_id = int(chain_row[0])
            chain_name = str(chain_row[1])
            chain_basket_items = []

            for matched_item in matched_items:
                product_id = matched_item.product_id
                if product_id is None or product_id not in product_lookup:
                    unmatched_items.append(matched_item.input_value)
                    continue

                product_row = product_lookup[product_id]
                chain_basket_items.append(
                    {
                        "product_id": product_id,
                        "product_name": product_row["name"],
                        "barcode": product_row["barcode"],
                        "quantity": matched_item.quantity,
                        "unit_price": price_lookup.get((chain_id, product_id)),
                    }
                )

            chain_inputs.append(
                {
                    "chain_id": chain_id,
                    "chain_name": chain_name,
                    "basket_items": chain_basket_items,
                }
            )

        chain_inputs.sort(
            key=lambda chain_input: self._chain_sort_key(chain_input),
        )
        return self._engine.build_comparison_result(
            chain_results_input=chain_inputs,
            unmatched_items=unmatched_items,
        )

    def _chain_sort_key(self, chain_input: dict[str, object]) -> tuple[bool, float, str]:
        chain_result = self._engine.build_chain_result(
            chain_id=int(chain_input["chain_id"]),
            chain_name=str(chain_input["chain_name"]),
            basket_items=chain_input["basket_items"],
        )
        return (
            not chain_result.is_complete_basket,
            chain_result.total_price,
            chain_result.chain_name,
        )

    def _load_products(self, product_ids: list[int]) -> dict[int, dict[str, str]]:
        unique_ids = sorted(set(product_ids))
        placeholders = ", ".join(["?"] * len(unique_ids))
        rows = self._connection.execute(
            f"SELECT id, name, barcode FROM products WHERE id IN ({placeholders})",
            tuple(unique_ids),
        ).fetchall()
        return {
            int(row[0]): {"name": str(row[1]), "barcode": str(row[2])}
            for row in rows
        }

    def _load_chain_min_prices(self, product_ids: object) -> dict[tuple[int, int], float]:
        ids = sorted(set(int(product_id) for product_id in product_ids))
        placeholders = ", ".join(["?"] * len(ids))
        rows = self._connection.execute(
            f"""
            SELECT chain_id, product_id, MIN(CAST(price AS REAL))
            FROM prices
            WHERE product_id IN ({placeholders})
            GROUP BY chain_id, product_id
            """,
            tuple(ids),
        ).fetchall()
        return {(int(row[0]), int(row[1])): float(row[2]) for row in rows}


class CliMatcher:
    """Product matcher for CLI basket-input commands."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._engine = BasketEngine()

    def to_basket_item(
        self,
        *,
        basket_id: int,
        input_type: str,
        input_value: str,
        quantity: int,
    ) -> BasketItem:
        if input_type == "barcode":
            return self._match_barcode(
                basket_id=basket_id,
                barcode=input_value,
                quantity=quantity,
            )
        if input_type == "name":
            return self._match_name(
                basket_id=basket_id,
                name=input_value,
                quantity=quantity,
            )
        raise ValueError("input_type must be 'barcode' or 'name'")

    def _match_barcode(self, *, basket_id: int, barcode: str, quantity: int) -> BasketItem:
        product_rows = self._connection.execute(
            "SELECT id, barcode, name FROM products"
        ).fetchall()
        products_by_barcode = {
            str(row[1]): {"id": int(row[0]), "barcode": str(row[1]), "name": str(row[2])}
            for row in product_rows
        }
        matched = self._engine.match_input_item_by_barcode(
            barcode=barcode,
            quantity=quantity,
            products_by_barcode=products_by_barcode,
        )
        return BasketItem(
            id=None,
            basket_id=basket_id,
            product_id=matched["product_id"],
            input_value=matched["input_value"],
            input_type=matched["input_type"],
            quantity=matched["quantity"],
            match_status=matched["match_status"],
        )

    def _match_name(self, *, basket_id: int, name: str, quantity: int) -> BasketItem:
        normalized_name = normalize_product_name(name)
        if not normalized_name:
            raise ValueError("input_value is required")

        if quantity <= 0:
            raise ValueError("quantity must be a positive integer")

        row = self._connection.execute(
            """
            SELECT id, normalized_name
            FROM products
            WHERE normalized_name = ?
            ORDER BY id
            LIMIT 1
            """,
            (normalized_name,),
        ).fetchone()

        if row is None:
            return BasketItem(
                id=None,
                basket_id=basket_id,
                product_id=None,
                input_value=name.strip(),
                input_type="name",
                quantity=quantity,
                match_status=MatchStatus.UNMATCHED.value,
            )

        return BasketItem(
            id=None,
            basket_id=basket_id,
            product_id=int(row[0]),
            input_value=name.strip(),
            input_type="name",
            quantity=quantity,
            match_status=MatchStatus.MATCHED.value,
        )


def build_application_service(connection: sqlite3.Connection) -> ApplicationService:
    """Build the application facade with SQLite-backed collaborators."""
    data_loader = PriceDataLoader(connection)
    basket_repository = BasketRepository(connection)
    comparison_service = SqliteBasketComparisonService(connection)
    chain_repository = SqliteChainReadRepository(connection)

    return ApplicationService(
        load_prices_use_case=LoadPricesUseCase(loader=CliLoadDispatcher(data_loader)),
        add_basket_item_use_case=AddBasketItemUseCase(basket_repository=basket_repository),
        compare_basket_use_case=CompareBasketUseCase(
            basket_repository=basket_repository,
            comparison_service=comparison_service,
        ),
        list_chains_use_case=ListChainsUseCase(chain_repository=chain_repository),
        update_basket_item_quantity_use_case=UpdateBasketItemQuantityUseCase(
            basket_repository=basket_repository
        ),
        remove_basket_item_use_case=RemoveBasketItemUseCase(
            basket_repository=basket_repository
        ),
        clear_basket_use_case=ClearBasketUseCase(basket_repository=basket_repository),
        get_basket_state_use_case=GetBasketStateUseCase(
            basket_repository=basket_repository
        ),
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="smart-basket", description="Local basket comparison CLI")
    parser.add_argument(
        "--db-path",
        default="data/generated/smart_basket.sqlite",
        help="SQLite database path (default: data/generated/smart_basket.sqlite)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    load_parser = subparsers.add_parser("load", help="Load local data files into SQLite")
    load_parser.add_argument("entity", choices=["products", "stores", "prices"])
    load_parser.add_argument("source_path", help="Path to local source file")
    load_parser.add_argument("--mode", choices=["append", "replace"], default="append")

    add_parser = subparsers.add_parser("add-item", help="Add one item to a basket")
    add_parser.add_argument("basket_id", type=int)
    add_parser.add_argument("input_value")
    add_parser.add_argument("--input-type", choices=["barcode", "name"], default="barcode")
    add_parser.add_argument("--quantity", type=int, default=1)

    compare_parser = subparsers.add_parser("compare", help="Compare one basket across chains")
    compare_parser.add_argument("basket_id", type=int)

    return parser


def _print_comparison(result: BasketComparisonResult, stdout: TextIO) -> None:
    if not result.ranked_chains:
        print("No chain comparison results available.", file=stdout)
    else:
        print("Ranked chain comparison:", file=stdout)
        for index, chain_result in enumerate(result.ranked_chains, start=1):
            completeness = "complete" if chain_result.is_complete_basket else "partial"
            print(
                f"{index}. {chain_result.chain_name} | total={chain_result.total_price:.2f} | "
                f"status={completeness} | found={chain_result.found_items_count} | "
                f"missing={chain_result.missing_items_count}",
                file=stdout,
            )
            for line in chain_result.basket_lines:
                unit_price_text = "N/A" if line.unit_price is None else f"{line.unit_price:.2f}"
                line_total_text = "N/A" if line.line_price is None else f"{line.line_price:.2f}"
                print(
                    f"   - {line.product_name} (qty={line.quantity}) "
                    f"unit={unit_price_text} line={line_total_text} "
                    f"status={line.availability_status.value}",
                    file=stdout,
                )
            if chain_result.missing_items:
                missing_text = ", ".join(chain_result.missing_items)
                print(f"   Missing items: {missing_text}", file=stdout)

    unmatched = sorted(result.unmatched_items)
    if unmatched:
        print(f"Unmatched items: {', '.join(unmatched)}", file=stdout)
    else:
        print("Unmatched items: none", file=stdout)


def run_cli(argv: list[str] | None = None, *, stdout: TextIO | None = None, stderr: TextIO | None = None) -> int:
    """Run the CLI command and return an exit code."""
    output = stdout or sys.stdout
    error_output = stderr or sys.stderr
    parser = _build_parser()

    try:
        args = parser.parse_args(argv)
        db_path = Path(args.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        connection = ConnectionFactory.create_connection(str(db_path))
        create_schema(connection)

        app_service = build_application_service(connection)
        matcher = CliMatcher(connection)

        if args.command == "load":
            load_request = CliLoadRequest(
                entity=args.entity,
                source_path=args.source_path,
                mode=args.mode,
            )
            result = app_service.load_prices(load_request)
            if result.success:
                print(
                    f"Loaded {result.job.entity}: accepted={result.accepted_count}, "
                    f"rejected={result.rejected_count}",
                    file=output,
                )
                return 0

            print(
                f"Load failed for {result.job.entity}: "
                + "; ".join(result.errors),
                file=error_output,
            )
            return 1

        if args.command == "add-item":
            item = matcher.to_basket_item(
                basket_id=args.basket_id,
                input_type=args.input_type,
                input_value=args.input_value,
                quantity=args.quantity,
            )
            saved = app_service.add_basket_item(item)
            print(
                f"Added basket item #{saved.id}: value='{saved.input_value}', "
                f"status={saved.match_status}, quantity={saved.quantity}",
                file=output,
            )
            return 0

        if args.command == "compare":
            result = app_service.compare_basket(args.basket_id)
            _print_comparison(result, output)
            return 0

        raise ValueError("unsupported command")
    except (ValueError, TypeError, sqlite3.DatabaseError) as exc:
        print(f"Error: {exc}", file=error_output)
        return 1


def main() -> None:
    """Console entry point."""
    raise SystemExit(run_cli())


if __name__ == "__main__":
    main()
