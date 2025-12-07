# Copyright (c) 2025, KCSC and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, nowdate, flt, rounded

def check_lease_end_and_create_invoice():
    today = getdate(nowdate())

    leases = frappe.get_all(
        "Lease Contract",
        filters={
            "status": "Rent",
            "docstatus": 1,
        },
        fields=["name", "lease_end"]
    )
    if not leases:
        frappe.throw("No active Lease Contracts found.")

    for lease in leases:
        if lease.lease_end and today > getdate(lease.lease_end):
            continue

        lease_doc = frappe.get_doc("Lease Contract", lease.name)
        company_doc = frappe.get_doc("Company", lease_doc.owner_lessor)
        schedules = frappe.get_all(
            "Lease Contract Schedule",
            filters={"lease_contract": lease_doc.name, "docstatus": 1},
            fields=["name"]
        )
        if not schedules:
            frappe.throw(f"No schedules found for Lease Contract {lease_doc.name}")

        for sched in schedules:
            schedule_doc = frappe.get_doc("Lease Contract Schedule", sched.name)
            
            for row in schedule_doc.invoice:
                
                if row.is_allowance:
                    continue
                
                if row.invoice_number:
                    continue
                
                row_start_date = getdate(row.lease_start)
                if row_start_date > today:
                    continue
                
                if not lease_doc.contract_multi_period:
                    create_individual_invoice(lease_doc, row, schedule_doc)
                elif lease_doc.contract_multi_period:
                    create_multi_period_invoices(lease_doc, row, schedule_doc)
                
        if lease_doc.other_service:
            for service in lease_doc.other_service:
                if service.invoice_number:
                    continue
                if service.invoice_date and service.invoice_date <= today:
                    invoice = frappe.new_doc("Sales Invoice")
                    invoice.customer = lease_doc.tenant_lessee
                    posting_date = service.invoice_date
                    due_date = service.invoice_date
                    invoice.set_posting_time = 1
                    invoice.posting_date = str(posting_date)
                    invoice.due_date = str(due_date)
                    invoice.custom_lease_contract = lease_doc.name
                    invoice.debit_to = company_doc.default_receivable_account if company_doc.default_receivable_account else frappe.throw(f"Please set Default Receivable Account in Company Settings")
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
                        "income_account": (
                            company_doc.default_income_account
                            if company_doc.default_income_account
                            else frappe.throw("Please set Default Income Account in Company Settings")
                        ),
                        "enable_deferred_revenue": 1 if posting_date != due_date else 0,
                        "service_start_date": posting_date,
                        "service_end_date": due_date,
                    })

                    setup_invoice_taxes(invoice, company_doc.name)
                    invoice.insert(ignore_permissions=True)
                    invoice.submit()
                    service.invoice_number = invoice.name
                    service.db_update()
                

def create_individual_invoice(lease_doc, payment_row, schedule_doc):
    try:
        company_doc = frappe.get_doc("Company", lease_doc.owner_lessor)
        if not lease_doc.tenant_lessee:
            frappe.throw(f"Lease Contract {lease_doc.name} has no Tenant/Customer linked!")
            return

        invoice = frappe.new_doc("Sales Invoice")
        invoice.customer = lease_doc.tenant_lessee

        posting_date = payment_row.lease_start
        due_date = payment_row.lease_end
        invoice.set_posting_time = 1
        invoice.posting_date = str(posting_date)
        invoice.due_date = str(due_date)
        invoice.custom_lease_contract = lease_doc.name
        invoice.debit_to = company_doc.default_receivable_account if company_doc.default_receivable_account else frappe.throw(f"Please set Default Receivable Account in Company Settings")

        item_codes = frappe.get_all("Lease Contract Details",
            filters={
                "parent": lease_doc.name,
            },
            fields=["rent_item", "amount"]
        )                
         
        if not item_codes:
            frappe.throw(f"No items found in Lease Contract {lease_doc.name} to create invoice.")

        total_months = rounded(flt(getattr(lease_doc, 'period_in_months', 0)) / flt(getattr(lease_doc, 'billing_frequency', 1)), 6)
        if not lease_doc.contract_multi_period:
            if lease_doc.allowance_period and lease_doc.in_period:
                total_months = rounded(total_months - flt(lease_doc.allowance_period), 6)
        
        for item in item_codes:
            item_doc = frappe.get_doc("Item", item.rent_item)
            if not lease_doc.contract_multi_period:
                item_rate = rounded(flt(item.amount) / total_months, 6)
                
                invoice.append("items", {
                    "item_code": item.rent_item,
                    "item_name": item_doc.item_name,
                    "item_group": item_doc.item_group,
                    "qty": 1,
                    "rate": item_rate,
                    "uom": item_doc.stock_uom,
                    "income_account": company_doc.default_income_account if company_doc.default_income_account else frappe.throw(f"Please set Default Income Account in Company Settings"),
                    "enable_deferred_revenue": 1,
                    "service_start_date": posting_date,
                    "service_end_date": due_date,
                })

        setup_invoice_taxes(invoice, company_doc.name)

        invoice.insert(ignore_permissions=True)
        invoice.submit()

        frappe.msgprint(f"Sales Invoice {invoice.name} created for period {payment_row.lease_start} to {payment_row.lease_end}", alert=True, indicator="green")

        payment_row.invoice_number = invoice.name
        payment_row.invoice_status = invoice.status
        schedule_doc.save(ignore_permissions=True)

    except Exception as e:
        frappe.throw(f"Failed to create invoice for payment period: {str(e)}")
        
def create_multi_period_invoices(lease_doc, payment_row, schedule_doc):
    try:
        company_doc = frappe.get_doc("Company", lease_doc.owner_lessor)
        if not lease_doc.tenant_lessee:
            frappe.throw(f"Lease Contract {lease_doc.name} has no Tenant/Customer linked!")

        invoice = frappe.new_doc("Sales Invoice")
        invoice.customer = lease_doc.tenant_lessee

        posting_date = payment_row.lease_start
        due_date = payment_row.lease_end
        invoice.set_posting_time = 1
        invoice.posting_date = str(posting_date)
        invoice.due_date = str(due_date)
        invoice.custom_lease_contract = lease_doc.name
        invoice.debit_to = company_doc.default_receivable_account or frappe.throw("Please set Default Receivable Account in Company Settings")

        period = None
        for p in lease_doc.period_details:
            if getdate(p.from_date) <= getdate(posting_date) <= getdate(p.to_date):
                period = p
                break

        if not period:
            frappe.throw(f"No matching period detail found for posting date {posting_date} in Lease {lease_doc.name}")

        period_months = flt(period.month_in_period)
        if period_months <= 0:
            frappe.throw("Invalid 'month_in_period' value in period details.")

        if lease_doc.allowance_period and lease_doc.in_period and period == lease_doc.period_details[0]:
            period_months = rounded(period_months - flt(lease_doc.allowance_period), 6)

        service_rent_monthly = rounded(flt(period.service_amount) / period_months, 6)
        space_rent_monthly = rounded(flt(period.space_amount) / period_months, 6)
        
        for rent_item in lease_doc.rent_details:
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
                "income_account": company_doc.default_income_account or frappe.throw("Please set Default Income Account in Company Settings"),
                "enable_deferred_revenue": 1,
                "service_start_date": posting_date,
                "service_end_date": due_date,
            })

        setup_invoice_taxes(invoice, company_doc.name)

        invoice.insert(ignore_permissions=True)
        invoice.submit()

        payment_row.invoice_number = invoice.name
        payment_row.invoice_status = invoice.status
        schedule_doc.save(ignore_permissions=True)

    except Exception as e:
        frappe.throw(f"Failed to create multi-period invoice: {str(e)}")

def setup_invoice_taxes(invoice, company):
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