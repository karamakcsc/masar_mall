# Copyright (c) 2025, KCSC and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, nowdate

def check_lease_end_and_create_invoice():
    today = getdate(nowdate())

    leases = frappe.get_all(
        "Lease Contract",
        filters={
            "status": "Rent",
            "docstatus": 1
        },
        fields=["name", "lease_end"]
    )
    if not leases:
        frappe.throw("No active Lease Contracts found.")

    for lease in leases:
        if lease.lease_end and today > getdate(lease.lease_end):
            continue

        lease_doc = frappe.get_doc("Lease Contract", lease.name)
        
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
                
                create_individual_invoice(lease_doc, row, schedule_doc)

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
            
        for item in item_codes:
            invoice.append("items", {
                "item_code": item.rent_item,
                "item_name": frappe.get_value("Item", item.item_code, "item_name"),
                "item_group": frappe.get_value("Item", item.item_code, "item_group"),
                # "description": f"Lease payment for {payment_row.lease_start} to {payment_row.lease_end}",
                "qty": 1,
                "rate": item.amount,
                "amount": item.amount,
                "uom": frappe.get_value("Item", item.item_code, "stock_uom"),
                "income_account": company_doc.default_income_account if company_doc.default_income_account else frappe.throw(f"Please set Default Income Account in Company Settings"),
                "enable_deferred_revenue": 1,
                "service_start_date": posting_date,
                "service_end_date": due_date,
            })

        invoice.insert(ignore_permissions=True)
        invoice.submit()

        frappe.msgprint(f"Sales Invoice {invoice.name} created for period {payment_row.lease_start} to {payment_row.lease_end}", alert=True, indicator="green")

        payment_row.invoice_number = invoice.name
        payment_row.invoice_status = invoice.status
        schedule_doc.save(ignore_permissions=True)

        frappe.msgprint(f"Updated schedule row with invoice {invoice.name}", alert=True, indicator="green")

    except Exception as e:
        frappe.throw(f"Failed to create invoice for payment period: {str(e)}")