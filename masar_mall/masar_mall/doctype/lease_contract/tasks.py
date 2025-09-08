# Copyright (c) 2025, KCSC and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, nowdate


def all():
    frappe.logger().info("This runs on every scheduler tick")


def daily():
    frappe.logger().info("This runs daily")
    check_lease_end_and_create_invoice()


def hourly():
    frappe.logger().info("This runs hourly")


def weekly():
    frappe.logger().info("This runs weekly")


def monthly():
    frappe.logger().info("This runs monthly")


def check_lease_end_and_create_invoice():
    """Check all Lease Contracts daily and create Sales Invoice for each payment period"""
    today = getdate(nowdate())

    # Get all submitted lease contracts
    leases = frappe.get_all(
        "Lease Contract",
        filters={
            "is_stopped": 0,
            "docstatus": 1
        },
        fields=["name", "tenant_lessee", "lease_start", "lease_end"]
    )

    if not leases:
        frappe.logger().info(f"🔎 No active Lease Contracts found.")
        return

    for lease in leases:
        try:
            lease_doc = frappe.get_doc("Lease Contract", lease.name)
            
            # Get all schedules for this lease
            schedules = frappe.get_all(
                "Lease Contract Schedule",
                filters={"lease_contract": lease_doc.name, "docstatus": 1},
                fields=["name"]
            )

            if not schedules:
                frappe.logger().info(f"⚠️ No schedules found for Lease Contract {lease_doc.name}")
                continue

            # Process each schedule
            for sched in schedules:
                schedule_doc = frappe.get_doc("Lease Contract Schedule", sched.name)
                
                # Create invoice for each row in the schedule
                for row in schedule_doc.invoice:
                    # Skip allowance/free months
                    if getattr(row, "is_allowance", 0):
                        continue
                    
                    # Skip if invoice already exists for this row
                    if getattr(row, "invoice_number", None):
                        continue
                    
                    # ✅ ONLY create invoice if lease_start matches today
                    row_start_date = getdate(row.lease_start)
                    if row_start_date != today:
                        continue  # Skip this row - not due today
                    
                    # Create individual invoice for this payment period
                    create_individual_invoice(lease_doc, row, schedule_doc)

        except Exception as e:
            frappe.logger().error(f"❌ Error processing lease {lease.name}: {str(e)}")
            continue


def create_individual_invoice(lease_doc, payment_row, schedule_doc):
    """Create a single Sales Invoice for one payment period/row"""
    try:
        if not lease_doc.tenant_lessee:
            frappe.throw(f"❌ Lease Contract {lease_doc.name} has no Tenant/Customer linked!")
            return

        # Create new Sales Invoice
        invoice = frappe.new_doc("Sales Invoice")
        invoice.customer = lease_doc.tenant_lessee

        # Set posting dates from the payment row
        posting_date = payment_row.lease_start
        due_date = payment_row.lease_end
        invoice.set_posting_time = 1
        invoice.posting_date = str(posting_date)
        invoice.due_date = str(due_date)
        invoice.custom_lease_contract = lease_doc.name

        # Get item code
        item_code = getattr(payment_row, "rent_item", None) or "Rent"
        if not frappe.db.exists("Item", item_code):
            frappe.throw(f"❌ Item {item_code} not found. Please create it in Item master.")
            return

        # Add single item for this payment period
        invoice.append("items", {
            "item_code": item_code,
            "description": f"Lease payment for {payment_row.lease_start} to {payment_row.lease_end}",
            "qty": 1,
            "rate": payment_row.amount,
            "amount": payment_row.amount,
            "uom": "Nos",
            "enable_deferred_revenue": 1,
            "service_start_date": posting_date,
            "service_end_date": due_date,
        })

        # Insert and submit invoice
        invoice.insert(ignore_permissions=True)
        invoice.submit()

        frappe.logger().info(f"✅ Sales Invoice {invoice.name} created for period {payment_row.lease_start} to {payment_row.lease_end}")

        # Update this specific row in the schedule
        payment_row.invoice_number = invoice.name
        payment_row.invoice_status = invoice.status
        schedule_doc.save(ignore_permissions=True)

        frappe.logger().info(f"🔄 Updated schedule row with invoice {invoice.name}")

    except Exception as e:
        frappe.logger().error(f"❌ Failed to create invoice for payment period: {str(e)}")
        raise