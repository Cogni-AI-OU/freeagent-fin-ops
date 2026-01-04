import argparse
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO

from typing import Any

from unittest.mock import ANY, patch

from scripts import fa_cli

TEST_OAUTH_SECRET = "dummy-oauth-secret"  # pragma: allowlist secret


class BankFeedsTests(unittest.TestCase):
    @patch("scripts.fa_cli.paginate_get")
    def test_bank_feeds_list(self, paginate_get: Any) -> None:
        paginate_get.return_value = [
            {
                "url": "https://api.example.com/bank_feeds/1",
                "bank_account": "https://api.example.com/bank_accounts/1",
                "state": "active",
                "feed_type": "open_banking",
            }
        ]
        args = argparse.Namespace(
            per_page=5,
            page=2,
            format="json",
            max_pages=None,
        )
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_bank_feeds_list(args, config, store)
        payload = json.loads(buf.getvalue())

        self.assertEqual(payload[0]["state"], "active")
        paginate_get.assert_called_once_with(
            config,
            store,
            "/bank_feeds",
            params={"per_page": 5, "page": 2},
            collection_key="bank_feeds",
            max_pages=None,
        )

    @patch("scripts.fa_cli.api_request")
    def test_bank_feeds_get(self, api_request_mock: Any) -> None:
        api_request_mock.return_value.json.return_value = {
            "bank_feed": {
                "url": "https://api.example.com/bank_feeds/1",
                "bank_account": "https://api.example.com/bank_accounts/1",
                "state": "active",
                "feed_type": "open_banking",
                "bank_service_name": "ExampleBank",
            }
        }
        args = argparse.Namespace(id="1", format="json")
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_bank_feeds_get(args, config, store)
        payload = json.loads(buf.getvalue())

        self.assertEqual(payload[0]["bank_service_name"], "ExampleBank")
        api_request_mock.assert_called_once_with("GET", config, store, "/bank_feeds/1")


class BankTransactionExplanationsTests(unittest.TestCase):
    @patch("scripts.fa_cli.paginate_get")
    def test_bank_transaction_explanations_list(self, paginate_get: Any) -> None:
        paginate_get.return_value = [
            {
                "url": "https://api.example.com/bank_transaction_explanations/1",
                "bank_account": "https://api.example.com/bank_accounts/1",
                "bank_transaction": "https://api.example.com/bank_transactions/1",
                "category": "https://api.example.com/categories/285",
                "dated_on": "2024-04-01",
                "description": "Card payment",
                "gross_value": "-10.00",
                "rebill_type": "price",
                "marked_for_review": True,
                "updated_at": "2024-04-02T10:00:00Z",
            }
        ]
        args = argparse.Namespace(
            bank_account="https://api.example.com/bank_accounts/1",
            from_date="2024-04-01",
            to_date="2024-04-30",
            updated_since="2024-04-01T00:00:00Z",
            per_page=25,
            page=1,
            format="json",
            max_pages=None,
            for_approval=False,
        )
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_bank_transaction_explanations_list(args, config, store)
        payload = json.loads(buf.getvalue())

        self.assertEqual(payload[0]["description"], "Card payment")
        paginate_get.assert_called_once_with(
            config,
            store,
            "/bank_transaction_explanations",
            params={
                "bank_account": "https://api.example.com/bank_accounts/1",
                "from_date": "2024-04-01",
                "to_date": "2024-04-30",
                "updated_since": "2024-04-01T00:00:00Z",
                "per_page": 25,
                "page": 1,
            },
            collection_key="bank_transaction_explanations",
            max_pages=None,
        )

    @patch("scripts.fa_cli.paginate_get")
    def test_bank_transaction_explanations_list_for_approval_filters(
        self, paginate_get: Any
    ) -> None:
        paginate_get.return_value = [
            {"url": "u1", "marked_for_review": True},
            {"url": "u2", "marked_for_review": False},
        ]
        args = argparse.Namespace(
            bank_account="https://api.example.com/bank_accounts/1",
            from_date=None,
            to_date=None,
            updated_since=None,
            per_page=25,
            page=1,
            format="json",
            max_pages=None,
            for_approval=True,
        )
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_bank_transaction_explanations_list(args, config, store)
        payload = json.loads(buf.getvalue())

        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["url"], "u1")

    @patch("scripts.fa_cli.api_request")
    def test_bank_transaction_explanations_get(self, api_request_mock: Any) -> None:
        api_request_mock.return_value.json.return_value = {
            "bank_transaction_explanation": {
                "url": "https://api.example.com/bank_transaction_explanations/2",
                "description": "Invoice payment",
            }
        }
        args = argparse.Namespace(id="2", format="json")
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_bank_transaction_explanations_get(args, config, store)
        payload = json.loads(buf.getvalue())

        self.assertEqual(payload[0]["description"], "Invoice payment")
        api_request_mock.assert_called_once_with(
            "GET", config, store, "/bank_transaction_explanations/2"
        )

    @patch("scripts.fa_cli.api_request")
    def test_bank_transaction_explanations_create(self, api_request_mock: Any) -> None:
        api_request_mock.return_value.json.return_value = {
            "bank_transaction_explanation": {
                "url": "https://api.example.com/bank_transaction_explanations/3"
            }
        }
        args = argparse.Namespace(
            body=json.dumps(
                {
                    "bank_transaction_explanation": {
                        "bank_transaction": "https://api.example.com/bank_transactions/1",
                        "gross_value": "-10.0",
                    }
                }
            ),
            dry_run=False,
        )
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        fa_cli.handle_bank_transaction_explanations_create(args, config, store)

        api_request_mock.assert_called_once_with(
            "POST",
            config,
            store,
            "/bank_transaction_explanations",
            json_body={
                "bank_transaction_explanation": {
                    "bank_transaction": "https://api.example.com/bank_transactions/1",
                    "gross_value": "-10.0",
                }
            },
        )

    @patch("scripts.fa_cli.api_request")
    def test_bank_transaction_explanations_update_dry_run(
        self, api_request_mock: Any
    ) -> None:
        args = argparse.Namespace(
            id="4",
            body=json.dumps(
                {
                    "bank_transaction_explanation": {
                        "description": "Updated",
                    }
                }
            ),
            dry_run=True,
        )
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_bank_transaction_explanations_update(args, config, store)

        self.assertIn("Updated", buf.getvalue())
        api_request_mock.assert_not_called()

    @patch("scripts.fa_cli.api_request")
    def test_bank_transaction_explanations_delete_dry_run(
        self, api_request_mock: Any
    ) -> None:
        args = argparse.Namespace(id="5", dry_run=True)
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_bank_transaction_explanations_delete(args, config, store)

        self.assertIn(
            "[dry-run] Would delete bank transaction explanation 5", buf.getvalue()
        )
        api_request_mock.assert_not_called()

    @patch("scripts.fa_cli.api_request")
    def test_bank_transaction_explanations_approve(self, api_request_mock: Any) -> None:
        api_request_mock.return_value.json.return_value = {
            "bank_transaction_explanation": {"url": "https://api.example.com/bte/1"}
        }
        args = argparse.Namespace(ids=["1", "2"], dry_run=False)
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        fa_cli.handle_bank_transaction_explanations_approve(args, config, store)

        api_request_mock.assert_any_call(
            "PUT",
            config,
            store,
            "/bank_transaction_explanations/1",
            json_body={"bank_transaction_explanation": {"marked_for_review": False}},
        )
        api_request_mock.assert_any_call(
            "PUT",
            config,
            store,
            "/bank_transaction_explanations/2",
            json_body={"bank_transaction_explanation": {"marked_for_review": False}},
        )

    def test_bank_transaction_explanations_approve_dry_run(self) -> None:
        args = argparse.Namespace(ids=["1"], dry_run=True)
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_bank_transaction_explanations_approve(args, config, store)

        self.assertIn("marked_for_review", buf.getvalue())


class ContactsListTests(unittest.TestCase):
    @patch("scripts.fa_cli.paginate_get")
    def test_contacts_list_outputs_json(self, paginate_get: Any) -> None:
        paginate_get.return_value = [
            {
                "url": "https://api.example.com/contacts/1",
                "first_name": "Ada",
                "last_name": "Lovelace",
                "organisation_name": "Analytical Engines",
                "email": "ada@example.com",
            }
        ]
        args = argparse.Namespace(
            view="active",
            search="Ada",
            updated_since=None,
            per_page=5,
            page=2,
            format="json",
            max_pages=None,
        )
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_contacts_list(args, config, store)
        output = buf.getvalue().strip()

        payload = json.loads(output)
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["first_name"], "Ada")

        paginate_get.assert_called_once_with(
            config,
            store,
            "/contacts",
            params={"view": "active", "search": "Ada", "per_page": 5, "page": 2},
            collection_key="contacts",
            max_pages=None,
        )


class ContactsGetTests(unittest.TestCase):
    @patch("scripts.fa_cli.api_request")
    def test_contacts_get(self, api_request_mock: Any) -> None:
        api_request_mock.return_value.json.return_value = {
            "contact": {
                "url": "https://api.example.com/contacts/1",
                "first_name": "Ada",
                "last_name": "Lovelace",
                "email": "ada@example.com",
                "address1": "6 High Street",
                "postcode": "E15 2GR",
            }
        }
        args = argparse.Namespace(id="1", format="json")
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_contacts_get(args, config, store)
        payload = json.loads(buf.getvalue())

        self.assertEqual(payload[0]["address1"], "6 High Street")
        api_request_mock.assert_called_once_with("GET", config, store, "/contacts/1")


class ContactsUpdateTests(unittest.TestCase):
    @patch("scripts.fa_cli.api_request")
    def test_contacts_update(self, api_request_mock: Any) -> None:
        api_request_mock.return_value.json.return_value = {
            "contact": {"url": "https://api.example.com/contacts/1"}
        }
        args = argparse.Namespace(
            id="1",
            body=json.dumps(
                {
                    "contact": {
                        "address1": "6 High Street",
                        "postcode": "E15 2GR",
                    }
                }
            ),
            dry_run=False,
        )
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_contacts_update(args, config, store)

        api_request_mock.assert_called_once_with(
            "PUT",
            config,
            store,
            "/contacts/1",
            json_body={"contact": {"address1": "6 High Street", "postcode": "E15 2GR"}},
        )

    def test_contacts_update_dry_run(self) -> None:
        args = argparse.Namespace(
            id="1",
            body=json.dumps(
                {"contact": {"address1": "6 High Street", "postcode": "E15 2GR"}}
            ),
            dry_run=True,
        )
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_contacts_update(args, config, store)
        payload = json.loads(buf.getvalue())

        self.assertEqual(payload["contact"]["address1"], "6 High Street")


class InvoicesListAllTests(unittest.TestCase):
    @patch("scripts.fa_cli.paginate_get")
    def test_invoices_list_all_plain_output(self, paginate_get: Any) -> None:
        paginate_get.return_value = [
            {
                "url": "https://api.example.com/invoices/1",
                "reference": "INV-001",
                "contact": "https://api.example.com/contacts/1",
                "status": "Open",
                "dated_on": "2024-01-01",
                "due_on": "2024-01-15",
                "total_value": 123.45,
            }
        ]
        args = argparse.Namespace(per_page=10, page=1, format="plain", max_pages=None)
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_invoices_list_all(args, config, store)
        output = buf.getvalue()

        self.assertIn("INV-001", output)
        paginate_get.assert_called_once_with(
            config,
            store,
            "/invoices",
            params={"per_page": 10, "page": 1},
            collection_key="invoices",
            max_pages=None,
        )


class BillsListAllTests(unittest.TestCase):
    @patch("scripts.fa_cli.paginate_get")
    def test_bills_list_all_plain_output(self, paginate_get: Any) -> None:
        paginate_get.return_value = [
            {
                "url": "https://api.example.com/bills/1",
                "reference": "BILL-001",
                "dated_on": "2024-02-01",
                "due_on": "2024-02-15",
                "total_value": 250.0,
                "status": "Open",
            }
        ]
        args = argparse.Namespace(per_page=10, page=1, format="plain", max_pages=None)
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_bills_list_all(args, config, store)
        output = buf.getvalue()

        self.assertIn("BILL-001", output)
        paginate_get.assert_called_once_with(
            config,
            store,
            "/bills",
            params={"per_page": 10, "page": 1},
            collection_key="bills",
            max_pages=None,
        )


class ExpensesListTests(unittest.TestCase):
    @patch("scripts.fa_cli.paginate_get")
    def test_expenses_list_with_filters(self, paginate_get: Any) -> None:
        paginate_get.return_value = [
            {
                "url": "https://api.example.com/expenses/1",
                "dated_on": "2024-03-01",
                "category": "https://api.example.com/categories/1",
                "description": "Train",
                "gross_value": 50.0,
                "currency": "GBP",
            }
        ]
        args = argparse.Namespace(
            view="recent",
            from_date="2024-03-01",
            to_date="2024-03-31",
            updated_since=None,
            project="https://api.example.com/projects/1",
            per_page=25,
            page=2,
            format="json",
            max_pages=None,
        )
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_expenses_list(args, config, store)
        output = buf.getvalue().strip()

        payload = json.loads(output)
        self.assertEqual(payload[0]["description"], "Train")
        paginate_get.assert_called_once_with(
            config,
            store,
            "/expenses",
            params={
                "view": "recent",
                "from_date": "2024-03-01",
                "to_date": "2024-03-31",
                "project": "https://api.example.com/projects/1",
                "per_page": 25,
                "page": 2,
            },
            collection_key="expenses",
            max_pages=None,
        )


class PayrollPeriodsTests(unittest.TestCase):
    @patch("scripts.fa_cli.api_request")
    def test_payroll_periods_list(self, api_request_mock: Any) -> None:
        api_request_mock.return_value.json.return_value = {
            "periods": [
                {
                    "url": "https://api.example.com/payroll/2026/0",
                    "period": 0,
                    "frequency": "Monthly",
                    "dated_on": "2025-04-25",
                    "status": "filed",
                }
            ]
        }
        args = argparse.Namespace(year=2026, format="json")
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_payroll_list_periods(args, config, store)
        output = json.loads(buf.getvalue())

        self.assertEqual(output[0]["period"], 0)
        api_request_mock.assert_called_once_with("GET", config, store, "/payroll/2026")


class PayrollPayslipsTests(unittest.TestCase):
    @patch("scripts.fa_cli.api_request")
    def test_payroll_payslips_list(self, api_request_mock: Any) -> None:
        api_request_mock.return_value.json.return_value = {
            "period": {
                "payslips": [
                    {
                        "user": "https://api.example.com/users/1",
                        "dated_on": "2025-04-25",
                        "tax_code": "1100L",
                        "basic_pay": "2500.0",
                        "tax_deducted": "500.0",
                        "employee_ni": "200.0",
                        "employer_ni": "300.0",
                        "net_pay": "2000.0",
                    }
                ]
            }
        }
        args = argparse.Namespace(year=2026, period=0, format="json")
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_payroll_list_payslips(args, config, store)
        output = json.loads(buf.getvalue())

        self.assertEqual(output[0]["tax_code"], "1100L")
        api_request_mock.assert_called_once_with(
            "GET", config, store, "/payroll/2026/0"
        )


class CompanyInfoTests(unittest.TestCase):
    @patch("scripts.fa_cli.api_request")
    def test_company_info(self, api_request_mock: Any) -> None:
        api_request_mock.return_value.json.return_value = {
            "company": {
                "url": "https://api.example.com/company",
                "name": "My Company",
                "subdomain": "myco",
                "type": "UkLimitedCompany",
                "currency": "GBP",
                "mileage_units": "miles",
                "company_start_date": "2020-05-01",
                "trading_start_date": "2020-06-01",
                "freeagent_start_date": "2020-05-01",
                "first_accounting_year_end": "2021-04-30",
                "sales_tax_registration_status": "Registered",
                "sales_tax_registration_number": "123456",
                "business_type": "Consulting",
                "business_category": "Software Development",
            }
        }
        args = argparse.Namespace(format="json")
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_company_info(args, config, store)
        payload = json.loads(buf.getvalue())

        self.assertEqual(payload[0]["name"], "My Company")
        api_request_mock.assert_called_once_with("GET", config, store, "/company")


class CompanyBusinessCategoriesTests(unittest.TestCase):
    @patch("scripts.fa_cli.api_request")
    def test_company_business_categories(self, api_request_mock: Any) -> None:
        api_request_mock.return_value.json.return_value = {
            "business_categories": ["Accounting", "Software Development"]
        }
        args = argparse.Namespace(format="json")
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_company_business_categories(args, config, store)
        payload = json.loads(buf.getvalue())

        self.assertEqual(payload[0]["business_category"], "Accounting")
        self.assertEqual(payload[1]["business_category"], "Software Development")
        api_request_mock.assert_called_once_with(
            "GET", config, store, "/company/business_categories"
        )


class CompanyTaxTimelineTests(unittest.TestCase):
    @patch("scripts.fa_cli.api_request")
    def test_company_tax_timeline(self, api_request_mock: Any) -> None:
        api_request_mock.return_value.json.return_value = {
            "timeline_items": [
                {
                    "description": "VAT Return 09 11",
                    "nature": "Electronic Submission and Payment Due",
                    "dated_on": "2011-11-07",
                    "amount_due": "-214.16",
                    "is_personal": False,
                }
            ]
        }
        args = argparse.Namespace(format="json")
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_company_tax_timeline(args, config, store)
        payload = json.loads(buf.getvalue())

        self.assertEqual(payload[0]["description"], "VAT Return 09 11")
        api_request_mock.assert_called_once_with(
            "GET", config, store, "/company/tax_timeline"
        )


class ReportsProfitLossTests(unittest.TestCase):
    @patch("scripts.fa_cli.api_request")
    def test_reports_profit_loss_summary(self, api_request_mock: Any) -> None:
        api_request_mock.return_value.json.return_value = {
            "profit_and_loss_summary": {
                "from": "2024-04-01",
                "to": "2025-03-31",
                "income": "1200",
                "expenses": "200",
                "operating_profit": "1000",
                "less": [{"title": "Corp. Tax", "total": "0"}],
                "retained_profit": "1000",
                "retained_profit_brought_forward": "50",
                "retained_profit_carried_forward": "1050",
            }
        }
        args = argparse.Namespace(
            from_date="2024-04-01",
            to_date="2025-03-31",
            accounting_period="2024/25",
            format="json",
        )
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_reports_profit_loss(args, config, store)
        payload = json.loads(buf.getvalue())

        self.assertEqual(payload["operating_profit"], "1000")
        api_request_mock.assert_called_once_with(
            "GET",
            config,
            store,
            "/accounting/profit_and_loss/summary",
            params={
                "from_date": "2024-04-01",
                "to_date": "2025-03-31",
                "accounting_period": "2024/25",
            },
        )


class TransactionsListTests(unittest.TestCase):
    @patch("scripts.fa_cli.paginate_get")
    def test_transactions_list(self, paginate_get: Any) -> None:
        paginate_get.return_value = [
            {
                "url": "https://api.example.com/accounting/transactions/1",
                "dated_on": "2024-04-01",
                "description": "Sale",
                "category": "https://api.example.com/categories/750",
                "category_name": "Bank Account",
                "nominal_code": "750-1",
                "debit_value": "30.0",
                "source_item_url": "https://api.example.com/bank_transaction_explanations/1",
                "created_at": "2024-04-02T10:00:00Z",
                "updated_at": "2024-04-02T10:00:00Z",
            }
        ]
        args = argparse.Namespace(
            from_date="2024-04-01",
            to_date="2024-04-30",
            nominal_code="750",
            per_page=10,
            page=1,
            format="json",
            max_pages=None,
        )
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_transactions_list(args, config, store)
        payload = json.loads(buf.getvalue())

        self.assertEqual(payload[0]["nominal_code"], "750-1")
        paginate_get.assert_called_once_with(
            config,
            store,
            "/accounting/transactions",
            params={
                "from_date": "2024-04-01",
                "to_date": "2024-04-30",
                "nominal_code": "750",
                "per_page": 10,
                "page": 1,
            },
            collection_key="transactions",
            max_pages=None,
        )


class TransactionsGetTests(unittest.TestCase):
    @patch("scripts.fa_cli.api_request")
    def test_transactions_get(self, api_request_mock: Any) -> None:
        api_request_mock.return_value.json.return_value = {
            "transaction": {
                "url": "https://api.example.com/accounting/transactions/2",
                "dated_on": "2024-05-01",
                "description": "Bill payment",
                "category_name": "Books and Journals",
                "nominal_code": "359",
            }
        }
        args = argparse.Namespace(id="2", format="json")
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_transactions_get(args, config, store)
        payload = json.loads(buf.getvalue())

        self.assertEqual(payload[0]["nominal_code"], "359")
        api_request_mock.assert_called_once_with(
            "GET", config, store, "/accounting/transactions/2"
        )


class JournalSetsTests(unittest.TestCase):
    @patch("scripts.fa_cli.paginate_get")
    def test_journal_sets_list(self, paginate_get: Any) -> None:
        paginate_get.return_value = [
            {
                "url": "https://api.example.com/journal_sets/1",
                "dated_on": "2024-04-01",
                "description": "Year-end adjustments",
                "updated_at": "2024-04-02T10:00:00Z",
                "tag": "APP",
            }
        ]
        args = argparse.Namespace(
            from_date="2024-04-01",
            to_date="2024-04-30",
            updated_since="2024-04-01T00:00:00Z",
            tag="APP",
            per_page=25,
            page=1,
            format="json",
            max_pages=None,
        )
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_journal_sets_list(args, config, store)
        payload = json.loads(buf.getvalue())

        self.assertEqual(payload[0]["description"], "Year-end adjustments")
        paginate_get.assert_called_once_with(
            config,
            store,
            "/journal_sets",
            params={
                "from_date": "2024-04-01",
                "to_date": "2024-04-30",
                "updated_since": "2024-04-01T00:00:00Z",
                "tag": "APP",
                "per_page": 25,
                "page": 1,
            },
            collection_key="journal_sets",
            max_pages=None,
        )

    @patch("scripts.fa_cli.api_request")
    def test_journal_sets_get(self, api_request_mock: Any) -> None:
        api_request_mock.return_value.json.return_value = {
            "journal_set": {
                "url": "https://api.example.com/journal_sets/2",
                "description": "Opening balances",
            }
        }
        args = argparse.Namespace(id="2", format="json")
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_journal_sets_get(args, config, store)
        payload = json.loads(buf.getvalue())

        self.assertEqual(payload[0]["description"], "Opening balances")
        api_request_mock.assert_called_once_with(
            "GET", config, store, "/journal_sets/2"
        )

    @patch("scripts.fa_cli.api_request")
    def test_journal_sets_opening_balances(self, api_request_mock: Any) -> None:
        api_request_mock.return_value.json.return_value = {
            "journal_set": {
                "url": "https://api.example.com/journal_sets/opening_balances",
                "description": "Opening Balances Journal Set",
            }
        }
        args = argparse.Namespace(format="json")
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_journal_sets_opening_balances(args, config, store)
        payload = json.loads(buf.getvalue())

        self.assertEqual(payload[0]["description"], "Opening Balances Journal Set")
        api_request_mock.assert_called_once_with(
            "GET", config, store, "/journal_sets/opening_balances"
        )

    @patch("scripts.fa_cli.api_request")
    def test_journal_sets_create(self, api_request_mock: Any) -> None:
        api_request_mock.return_value.json.return_value = {
            "journal_set": {"url": "https://api.example.com/journal_sets/3"}
        }
        args = argparse.Namespace(
            body=json.dumps({"journal_set": {"description": "Manual journals"}}),
            dry_run=False,
        )
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        fa_cli.handle_journal_sets_create(args, config, store)

        api_request_mock.assert_called_once_with(
            "POST",
            config,
            store,
            "/journal_sets",
            json_body={"journal_set": {"description": "Manual journals"}},
        )

    @patch("scripts.fa_cli.api_request")
    def test_journal_sets_update_dry_run(self, api_request_mock: Any) -> None:
        args = argparse.Namespace(
            id="5",
            body=json.dumps({"journal_set": {"description": "Updated"}}),
            dry_run=True,
        )
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_journal_sets_update(args, config, store)

        self.assertIn("Updated", buf.getvalue())
        api_request_mock.assert_not_called()

    @patch("scripts.fa_cli.api_request")
    def test_journal_sets_delete_dry_run(self, api_request_mock: Any) -> None:
        args = argparse.Namespace(id="6", dry_run=True)
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_journal_sets_delete(args, config, store)

        self.assertIn("[dry-run] Would delete journal set 6", buf.getvalue())
        api_request_mock.assert_not_called()


class AttachmentsListTests(unittest.TestCase):
    @patch("scripts.fa_cli.paginate_get")
    def test_attachments_list_filters(self, paginate_get: Any) -> None:
        paginate_get.return_value = [
            {
                "url": "https://api.example.com/attachments/1",
                "file_name": "receipt.pdf",
                "content_type": "application/pdf",
                "file_size": 1024,
                "description": "Receipt",
                "expires_at": "2024-12-31T00:00:00Z",
                "content_src": "https://example.com/receipt.pdf",
            }
        ]
        args = argparse.Namespace(
            attachable_type="Expense",
            attachable_id="123",
            per_page=5,
            page=1,
            format="json",
            max_pages=None,
        )
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_attachments_list(args, config, store)
        payload = json.loads(buf.getvalue())

        self.assertEqual(payload[0]["file_name"], "receipt.pdf")
        paginate_get.assert_called_once_with(
            config,
            store,
            "/attachments",
            params={
                "attachable_type": "Expense",
                "attachable_id": "123",
                "per_page": 5,
                "page": 1,
            },
            collection_key="attachments",
            max_pages=None,
        )


class AttachmentsGetTests(unittest.TestCase):
    @patch("scripts.fa_cli.api_request")
    def test_attachments_get(self, api_request_mock: Any) -> None:
        api_request_mock.return_value.json.return_value = {
            "attachment": {
                "url": "https://api.example.com/attachments/3",
                "file_name": "barcode.png",
                "content_type": "image/png",
            }
        }
        args = argparse.Namespace(id="3", format="json")
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_attachments_get(args, config, store)
        payload = json.loads(buf.getvalue())

        self.assertEqual(payload[0]["file_name"], "barcode.png")
        api_request_mock.assert_called_once_with("GET", config, store, "/attachments/3")


class AttachmentsUploadTests(unittest.TestCase):
    @patch("scripts.fa_cli.api_request")
    def test_attachments_upload(self, api_request_mock: Any) -> None:
        with tempfile.NamedTemporaryFile("wb", delete=False) as tmp:
            tmp.write(b"hello")
            tmp_path = tmp.name

        api_request_mock.return_value.json.return_value = {
            "attachment": {"url": "https://api.example.com/attachments/9"}
        }
        args = argparse.Namespace(
            file=tmp_path,
            description="Sample",
            attachable_type="Expense",
            attachable_id="999",
            content_type="text/plain",
            file_name="note.txt",
            dry_run=False,
            format="json",
        )
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()
        try:
            buf = StringIO()
            with redirect_stdout(buf):
                fa_cli.handle_attachments_upload(args, config, store)

            api_request_mock.assert_called_once_with(
                "POST",
                config,
                store,
                "/attachments",
                data={
                    "description": "Sample",
                    "content_type": "text/plain",
                    "file_name": "note.txt",
                    "attachable_type": "Expense",
                    "attachable_id": "999",
                },
                files=ANY,
            )
        finally:
            os.unlink(tmp_path)


class AttachmentsDeleteTests(unittest.TestCase):
    @patch("scripts.fa_cli.api_request")
    def test_attachments_delete(self, api_request_mock: Any) -> None:
        args = argparse.Namespace(id="4", dry_run=False)
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_attachments_delete(args, config, store)
        output = buf.getvalue().strip()

        self.assertIn("Deleted attachment 4", output)
        api_request_mock.assert_called_once_with(
            "DELETE", config, store, "/attachments/4"
        )


class UsersListTests(unittest.TestCase):
    @patch("scripts.fa_cli.paginate_get")
    def test_users_list(self, paginate_get: Any) -> None:
        paginate_get.return_value = [
            {
                "url": "https://api.example.com/users/1",
                "first_name": "Ada",
                "last_name": "Lovelace",
                "email": "ada@example.com",
                "role": "Director",
                "permission_level": 8,
                "opening_mileage": 0,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-02T00:00:00Z",
            }
        ]
        args = argparse.Namespace(
            view="staff", per_page=10, page=1, format="json", max_pages=None
        )
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_users_list(args, config, store)
        payload = json.loads(buf.getvalue())

        self.assertEqual(payload[0]["email"], "ada@example.com")
        paginate_get.assert_called_once_with(
            config,
            store,
            "/users",
            params={"view": "staff", "per_page": 10, "page": 1},
            collection_key="users",
            max_pages=None,
        )


class UsersGetTests(unittest.TestCase):
    @patch("scripts.fa_cli.api_request")
    def test_users_get(self, api_request_mock: Any) -> None:
        api_request_mock.return_value.json.return_value = {
            "user": {
                "url": "https://api.example.com/users/2",
                "first_name": "Grace",
                "last_name": "Hopper",
                "email": "grace@example.com",
                "role": "Accountant",
                "permission_level": 7,
                "opening_mileage": 0,
            }
        }
        args = argparse.Namespace(id="2", format="json")
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_users_get(args, config, store)
        payload = json.loads(buf.getvalue())

        self.assertEqual(payload[0]["email"], "grace@example.com")
        api_request_mock.assert_called_once_with("GET", config, store, "/users/2")


class UsersMeTests(unittest.TestCase):
    @patch("scripts.fa_cli.api_request")
    def test_users_me(self, api_request_mock: Any) -> None:
        api_request_mock.return_value.json.return_value = {
            "user": {
                "email": "me@example.com",
            }
        }
        args = argparse.Namespace(format="json")
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_users_me(args, config, store)
        payload = json.loads(buf.getvalue())

        self.assertEqual(payload[0]["email"], "me@example.com")
        api_request_mock.assert_called_once_with("GET", config, store, "/users/me")


class UsersDeleteTests(unittest.TestCase):
    @patch("scripts.fa_cli.api_request")
    def test_users_delete(self, api_request_mock: Any) -> None:
        args = argparse.Namespace(id="123", dry_run=False)
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_users_delete(args, config, store)
        output = buf.getvalue().strip()

        self.assertIn("Deleted user 123", output)
        api_request_mock.assert_called_once_with("DELETE", config, store, "/users/123")

    @patch("scripts.fa_cli.api_request")
    def test_users_delete_dry_run(self, api_request_mock: Any) -> None:
        args = argparse.Namespace(id="123", dry_run=True)
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_users_delete(args, config, store)
        output = buf.getvalue().strip()

        self.assertIn("[dry-run] Would delete user 123", output)
        api_request_mock.assert_not_called()


class UsersSetPermissionTests(unittest.TestCase):
    @patch("scripts.fa_cli.api_request")
    def test_users_set_permission(self, api_request_mock: Any) -> None:
        api_request_mock.return_value.json.return_value = {
            "user": {"permission_level": 0}
        }
        args = argparse.Namespace(id="123", permission_level=0, dry_run=False)
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_users_update_permission(args, config, store)
        output = json.loads(buf.getvalue())

        self.assertEqual(output["user"]["permission_level"], 0)
        api_request_mock.assert_called_once_with(
            "PUT",
            config,
            store,
            "/users/123",
            json_body={"user": {"permission_level": 0}},
        )

    def test_users_set_permission_dry_run(self) -> None:
        args = argparse.Namespace(id="123", permission_level=0, dry_run=True)
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_users_update_permission(args, config, store)
        payload = json.loads(buf.getvalue())

        self.assertEqual(payload["user"]["permission_level"], 0)


class UsersGetPermissionTests(unittest.TestCase):
    @patch("scripts.fa_cli.api_request")
    def test_users_get_permission(self, api_request_mock: Any) -> None:
        api_request_mock.return_value.json.return_value = {
            "user": {"permission_level": 5}
        }
        args = argparse.Namespace(id="123")
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_users_permission(args, config, store)
        payload = json.loads(buf.getvalue())

        self.assertEqual(payload["permission_level"], 5)
        api_request_mock.assert_called_once_with("GET", config, store, "/users/123")


class UsersSetHiddenTests(unittest.TestCase):
    @patch("scripts.fa_cli.api_request")
    def test_users_set_hidden(self, api_request_mock: Any) -> None:
        api_request_mock.return_value.json.return_value = {"user": {"hidden": True}}
        args = argparse.Namespace(id="123", hidden=True, dry_run=False)
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_users_set_hidden(args, config, store)
        payload = json.loads(buf.getvalue())

        self.assertTrue(payload["user"]["hidden"])
        api_request_mock.assert_called_once_with(
            "PUT", config, store, "/users/123", json_body={"user": {"hidden": True}}
        )

    def test_users_set_hidden_dry_run(self) -> None:
        args = argparse.Namespace(id="123", hidden=False, dry_run=True)
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_users_set_hidden(args, config, store)
        payload = json.loads(buf.getvalue())

        self.assertFalse(payload["user"]["hidden"])


class TimeslipsListTests(unittest.TestCase):
    @patch("scripts.fa_cli.paginate_get")
    def test_timeslips_list_with_filters(self, paginate_get: Any) -> None:
        paginate_get.return_value = [
            {
                "url": "https://api.example.com/timeslips/1",
                "user": "https://api.example.com/users/1",
                "project": "https://api.example.com/projects/1",
                "task": "https://api.example.com/tasks/1",
                "dated_on": "2024-03-10",
                "hours": 2.5,
                "billable": True,
                "billed_on": None,
                "comment": "Consulting",
            }
        ]
        args = argparse.Namespace(
            user="https://api.example.com/users/1",
            project="https://api.example.com/projects/1",
            task="https://api.example.com/tasks/1",
            from_date="2024-03-01",
            to_date="2024-03-31",
            view="unbilled",
            per_page=10,
            page=1,
            format="json",
            max_pages=None,
        )
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_timeslips_list(args, config, store)
        payload = json.loads(buf.getvalue())

        self.assertEqual(payload[0]["hours"], 2.5)
        paginate_get.assert_called_once_with(
            config,
            store,
            "/timeslips",
            params={
                "user": "https://api.example.com/users/1",
                "project": "https://api.example.com/projects/1",
                "task": "https://api.example.com/tasks/1",
                "from_date": "2024-03-01",
                "to_date": "2024-03-31",
                "view": "unbilled",
                "per_page": 10,
                "page": 1,
            },
            collection_key="timeslips",
            max_pages=None,
        )


class TimeslipsDeleteTests(unittest.TestCase):
    @patch("scripts.fa_cli.api_request")
    def test_timeslips_delete(self, api_request_mock: Any) -> None:
        args = argparse.Namespace(id="25", dry_run=False)
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_timeslips_delete(args, config, store)
        output = buf.getvalue().strip()

        self.assertIn("Deleted timeslip 25", output)
        api_request_mock.assert_called_once_with(
            "DELETE", config, store, "/timeslips/25"
        )

    @patch("scripts.fa_cli.api_request")
    def test_timeslips_delete_dry_run(self, api_request_mock: Any) -> None:
        args = argparse.Namespace(id="25", dry_run=True)
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_timeslips_delete(args, config, store)
        output = buf.getvalue().strip()

        self.assertIn("[dry-run] Would delete timeslip 25", output)
        api_request_mock.assert_not_called()


class FinalAccountsListTests(unittest.TestCase):
    @patch("scripts.fa_cli.paginate_get")
    def test_final_accounts_list(self, paginate_get: Any) -> None:
        paginate_get.return_value = [
            {
                "url": "https://api.example.com/final_accounts_reports/2023-12-31",
                "period_ends_on": "2023-12-31",
                "period_starts_on": "2023-01-01",
                "filing_due_on": "2024-09-30",
                "filing_status": "draft",
                "filed_at": None,
                "filed_reference": None,
            }
        ]
        args = argparse.Namespace(per_page=10, page=1, format="json", max_pages=None)
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_final_accounts_list(args, config, store)
        payload = json.loads(buf.getvalue())

        self.assertEqual(payload[0]["filing_status"], "draft")
        paginate_get.assert_called_once_with(
            config,
            store,
            "/final_accounts_reports",
            params={"per_page": 10, "page": 1},
            collection_key="final_accounts_reports",
            max_pages=None,
        )


class FinalAccountsGetTests(unittest.TestCase):
    @patch("scripts.fa_cli.api_request")
    def test_final_accounts_get(self, api_request_mock: Any) -> None:
        api_request_mock.return_value.json.return_value = {
            "final_accounts_report": {
                "url": "https://api.example.com/final_accounts_reports/2023-12-31",
                "period_ends_on": "2023-12-31",
                "period_starts_on": "2023-01-01",
                "filing_due_on": "2024-09-30",
                "filing_status": "draft",
                "filed_at": None,
                "filed_reference": None,
            }
        }
        args = argparse.Namespace(period_ends_on="2023-12-31", format="json")
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_final_accounts_get(args, config, store)
        payload = json.loads(buf.getvalue())

        self.assertEqual(payload[0]["period_ends_on"], "2023-12-31")
        api_request_mock.assert_called_once_with(
            "GET", config, store, "/final_accounts_reports/2023-12-31"
        )


class FinalAccountsMarkFiledTests(unittest.TestCase):
    @patch("scripts.fa_cli.api_request")
    def test_final_accounts_mark_filed(self, api_request_mock: Any) -> None:
        api_request_mock.return_value.json.return_value = {
            "final_accounts_report": {
                "period_ends_on": "2023-12-31",
                "filing_status": "marked_as_filed",
            }
        }
        args = argparse.Namespace(period_ends_on="2023-12-31")
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_final_accounts_mark_as_filed(args, config, store)
        output = json.loads(buf.getvalue())

        self.assertEqual(
            output["final_accounts_report"]["filing_status"], "marked_as_filed"
        )
        api_request_mock.assert_called_once_with(
            "PUT", config, store, "/final_accounts_reports/2023-12-31/mark_as_filed"
        )


class FinalAccountsMarkUnfiledTests(unittest.TestCase):
    @patch("scripts.fa_cli.api_request")
    def test_final_accounts_mark_unfiled(self, api_request_mock: Any) -> None:
        api_request_mock.return_value.json.return_value = {
            "final_accounts_report": {
                "period_ends_on": "2023-12-31",
                "filing_status": "unfiled",
            }
        }
        args = argparse.Namespace(period_ends_on="2023-12-31")
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_final_accounts_mark_as_unfiled(args, config, store)
        output = json.loads(buf.getvalue())

        self.assertEqual(output["final_accounts_report"]["filing_status"], "unfiled")
        api_request_mock.assert_called_once_with(
            "PUT",
            config,
            store,
            "/final_accounts_reports/2023-12-31/mark_as_unfiled",
        )


class ProjectsListTests(unittest.TestCase):
    @patch("scripts.fa_cli.paginate_get")
    def test_projects_list(self, paginate_get: Any) -> None:
        paginate_get.return_value = [
            {
                "url": "https://api.example.com/projects/1",
                "name": "Alpha",
                "status": "active",
                "contact": "https://api.example.com/contacts/1",
                "currency": "GBP",
                "budget_units": "Hours",
                "budget": 100,
                "normal_billing_rate": 80,
                "started_on": "2024-01-01",
                "ended_on": None,
            }
        ]
        args = argparse.Namespace(
            view="active",
            updated_since=None,
            per_page=10,
            page=1,
            format="json",
            max_pages=None,
        )
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_projects_list(args, config, store)
        payload = json.loads(buf.getvalue())

        self.assertEqual(payload[0]["name"], "Alpha")
        paginate_get.assert_called_once_with(
            config,
            store,
            "/projects",
            params={"view": "active", "per_page": 10, "page": 1},
            collection_key="projects",
            max_pages=None,
        )


class ProjectsGetTests(unittest.TestCase):
    @patch("scripts.fa_cli.api_request")
    def test_projects_get(self, api_request_mock: Any) -> None:
        api_request_mock.return_value.json.return_value = {
            "project": {
                "url": "https://api.example.com/projects/2",
                "name": "Beta",
                "status": "completed",
                "contact": "https://api.example.com/contacts/2",
            }
        }
        args = argparse.Namespace(id="2", format="json")
        config = fa_cli.AppConfig(
            oauth_id="id",
            oauth_secret=TEST_OAUTH_SECRET,
            redirect_uri="http://localhost",
        )
        store = object()

        buf = StringIO()
        with redirect_stdout(buf):
            fa_cli.handle_projects_get(args, config, store)
        payload = json.loads(buf.getvalue())

        self.assertEqual(payload[0]["name"], "Beta")
        api_request_mock.assert_called_once_with("GET", config, store, "/projects/2")


if __name__ == "__main__":
    unittest.main()
