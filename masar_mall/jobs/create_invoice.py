# Copyright (c) 2025, KCSC and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, nowdate, flt, rounded


def check_lease_end_and_create_invoice():
    today = getdate(nowdate())

    try:
        leases = frappe.get_all(
            "Lease Contract",
            filters={
                "status": "Rent",
                "docstatus": 1,
            },
            fields=["name", "lease_end"]
        )
    except Exception as e:
        frappe.log_error(e, "Lease Invoice Job | Failed to fetch Lease Contracts")
        return

    if not leases:
        frappe.log_error("No active Lease Contracts found", "Lease Invoice Job")
        return

    for lease in leases:
        try:
            if lease.lease_end and today > getdate(lease.lease_end):
                continue

            lease_doc = frappe.get_doc("Lease Contract", lease.name)

            if not lease_doc.owner_lessor:
                frappe.log_error("Owner/Lessor not set", f"Lease Contract: {lease_doc.name}")
                continue

            company_doc = frappe.get_doc("Company", lease_doc.owner_lessor)

            schedules = frappe.get_all(
                "Lease Contract Schedule",
                filters={"lease_contract": lease_doc.name, "docstatus": 1},
                fields=["name"]
            )

            if not schedules:
                frappe.log_error("No schedules found", f"Lease Contract: {lease_doc.name}")
                continue

            for sched in schedules:
                try:
                    schedule_doc = frappe.get_doc("Lease Contract Schedule", sched.name)

                    for row in schedule_doc.invoice:

                        if row.is_allowance or row.invoice_number:
                            continue

                        if getdate(row.lease_start) > today:
                            continue

                        if not lease_doc.contract_multi_period:
                            create_individual_invoice(lease_doc, row, schedule_doc)
                        else:
                            create_multi_period_invoices(lease_doc, row, schedule_doc)

                except Exception as e:
                    frappe.log_error(e, f"Schedule Processing Error | Lease: {lease_doc.name} | Schedule: {sched.name}")
                    continue

            if lease_doc.other_service:
                for service in lease_doc.other_service:
                    try:
                        if service.invoice_number:
                            continue

                        if not service.invoice_date or service.invoice_date > today:
                            continue

                        if not lease_doc.tenant_lessee:
                            frappe.log_error("Tenant not set", f"Lease Contract: {lease_doc.name}")
                            continue

                        if not company_doc.default_receivable_account:
                            frappe.log_error("Default Receivable Account missing", f"Company: {company_doc.name}")
                            continue

                        if not company_doc.default_income_account:
                            frappe.log_error("Default Income Account missing", f"Company: {company_doc.name}")
                            continue

                        invoice = frappe.new_doc("Sales Invoice")
                        invoice.customer = lease_doc.tenant_lessee
                        invoice.set_posting_time = 1
                        invoice.posting_date = str(service.invoice_date)
                        invoice.due_date = str(service.invoice_date)
                        invoice.custom_lease_contract = lease_doc.name
                        invoice.debit_to = company_doc.default_receivable_account

                        item_doc = frappe.get_doc("Item", service.service_item)
                        service_rate = rounded(flt(service.rate), 6)

                        invoice.append("items", {
                            "item_code": service.service_item,
                            "item_name": service.item_name or item_doc.item_name,
                            "item_group": item_doc.item_group,
                            "qty": 1,
                            "rate": service_rate,
                            "amount": service_rate,
                            "uom": item_doc.stock_uom,
                            "income_account": company_doc.default_income_account,
                            "enable_deferred_revenue": 0,
                            "service_start_date": service.invoice_date,
                            "service_end_date": service.invoice_date,
                        })

                        setup_invoice_taxes(invoice, company_doc.name)
                        invoice.insert(ignore_permissions=True)

                        service.invoice_number = invoice.name
                        service.db_update()

                    except Exception as e:
                        frappe.log_error(e, f"Other Service Invoice Error | Lease: {lease_doc.name}")
                        continue

        except Exception as e:
            frappe.log_error(e, f"Lease Processing Error | Lease: {lease.name}")
            continue


def create_individual_invoice(lease_doc, payment_row, schedule_doc):
    try:
        if not lease_doc.tenant_lessee:
            frappe.log_error("Tenant not set", f"Lease Contract: {lease_doc.name}")
            return

        company_doc = frappe.get_doc("Company", lease_doc.owner_lessor)

        if not company_doc.default_receivable_account or not company_doc.default_income_account:
            frappe.log_error("Company accounts missing", f"Company: {company_doc.name}")
            return

        invoice = frappe.new_doc("Sales Invoice")
        invoice.customer = lease_doc.tenant_lessee
        invoice.set_posting_time = 1
        invoice.posting_date = str(payment_row.lease_start)
        invoice.due_date = str(payment_row.lease_end)
        invoice.custom_lease_contract = lease_doc.name
        invoice.debit_to = company_doc.default_receivable_account

        item_codes = frappe.get_all(
            "Lease Contract Details",
            filters={"parent": lease_doc.name, "amount": (">", 0)},
            fields=["rent_item", "amount"]
        )

        if not item_codes:
            frappe.log_error("No billable items", f"Lease Contract: {lease_doc.name}")
            return

        total_months = rounded(
            flt(getattr(lease_doc, "period_in_months", 0)) /
            flt(getattr(lease_doc, "billing_frequency", 1)),
            6
        )

        if lease_doc.allowance_period and lease_doc.in_period:
            total_months -= flt(lease_doc.allowance_period)

        for item in item_codes:
            item_doc = frappe.get_doc("Item", item.rent_item)
            item_rate = rounded(flt(item.amount) / total_months, 6)

            invoice.append("items", {
                "item_code": item.rent_item,
                "item_name": item_doc.item_name,
                "item_group": item_doc.item_group,
                "qty": 1,
                "rate": item_rate,
                "uom": item_doc.stock_uom,
                "income_account": company_doc.default_income_account,
                "enable_deferred_revenue": 1,
                "service_start_date": payment_row.lease_start,
                "service_end_date": payment_row.lease_end,
            })

        setup_invoice_taxes(invoice, company_doc.name)
        invoice.insert(ignore_permissions=True)

        payment_row.invoice_number = invoice.name
        payment_row.invoice_status = invoice.status
        schedule_doc.save(ignore_permissions=True)

    except Exception as e:
        frappe.log_error(e, f"Individual Invoice Error | Lease: {lease_doc.name}")


def create_multi_period_invoices(lease_doc, payment_row, schedule_doc):
    try:
        if not lease_doc.tenant_lessee:
            frappe.log_error("Tenant not set", f"Lease Contract: {lease_doc.name}")
            return

        company_doc = frappe.get_doc("Company", lease_doc.owner_lessor)

        if not company_doc.default_receivable_account or not company_doc.default_income_account:
            frappe.log_error("Company accounts missing", f"Company: {company_doc.name}")
            return

        invoice = frappe.new_doc("Sales Invoice")
        invoice.customer = lease_doc.tenant_lessee
        invoice.set_posting_time = 1
        invoice.posting_date = str(payment_row.lease_start)
        invoice.due_date = str(payment_row.lease_end)
        invoice.custom_lease_contract = lease_doc.name
        invoice.debit_to = company_doc.default_receivable_account

        period = None
        for p in lease_doc.period_details:
            if getdate(p.from_date) <= getdate(payment_row.lease_start) <= getdate(p.to_date):
                period = p
                break

        if not period:
            frappe.log_error("No matching period", f"Lease: {lease_doc.name} | Date: {payment_row.lease_start}")
            return

        period_months = flt(period.month_in_period)
        if lease_doc.allowance_period and lease_doc.in_period and period == lease_doc.period_details[0]:
            period_months -= flt(lease_doc.allowance_period)

        service_rent_monthly = rounded(flt(period.service_amount) / period_months, 6)
        space_rent_monthly = rounded(flt(period.space_amount) / period_months, 6)

        for rent_item in lease_doc.rent_details:
            if rent_item.amount <= 0:
                continue

            item_doc = frappe.get_doc("Item", rent_item.rent_item)
            monthly_rate = space_rent_monthly if rent_item.is_stock_item else service_rent_monthly
            invoice_rate = rounded(monthly_rate * flt(lease_doc.billing_frequency), 6)

            invoice.append("items", {
                "item_code": rent_item.rent_item,
                "item_name": item_doc.item_name,
                "item_group": item_doc.item_group,
                "qty": 1,
                "rate": invoice_rate,
                "uom": item_doc.stock_uom,
                "income_account": company_doc.default_income_account,
                "enable_deferred_revenue": 1,
                "service_start_date": payment_row.lease_start,
                "service_end_date": payment_row.lease_end,
            })

        setup_invoice_taxes(invoice, company_doc.name)
        invoice.insert(ignore_permissions=True)

        payment_row.invoice_number = invoice.name
        payment_row.invoice_status = invoice.status
        schedule_doc.save(ignore_permissions=True)

    except Exception as e:
        frappe.log_error(e, f"Multi Period Invoice Error | Lease: {lease_doc.name}")


def setup_invoice_taxes(invoice, company):
    try:
        cost_center = frappe.get_cached_value("Company", company, "cost_center")

        tax_accounts = [
            {
                "account_head": "220000003 - VAT - BM",
                "description": "VAT",
                "rate": 0,
            },
            {
                "account_head": "2210000001 - VAT 0 - BM",
                "description": "VAT 0",
                "rate": 0,
            }
        ]

        for tax in tax_accounts:
            invoice.append("taxes", {
                "charge_type": "On Net Total",
                "account_head": tax["account_head"],
                "description": tax["description"],
                "rate": tax["rate"],
                "included_in_print_rate": 0,
                "cost_center": cost_center
            })

    except Exception as e:
        frappe.log_error(e, f"Invoice Tax Setup Error | Company: {company}")
