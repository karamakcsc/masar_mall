import frappe
from frappe.utils import getdate, nowdate

def update_lease_schedule_status_from_invoice():
    """Update Lease Contract Schedule child table with status from Sales Invoice using Python dicts"""
    
    today = getdate(nowdate())

    # Step 1: Fetch all Sales Invoices at once
    invoices = frappe.get_all(
        "Sales Invoice",
        filters={"posting_date": ["<=", today]},
        fields=["name", "status"],
        ignore_permissions=True
    )

    if not invoices:
        frappe.logger().info("No Sales Invoices found for today or earlier.")
        return

    # Convert invoices list into a dictionary for quick lookup
    invoice_dict = {inv['name']: inv['status'] for inv in invoices}

    # Step 2: Fetch all Lease Contract Schedules with their invoice child tables
    schedules = frappe.get_all(
        "Lease Contract Schedule",
        filters={"docstatus": 1},
        fields=["name"],
        ignore_permissions=True
    )

    # Load all schedules into memory
    for sched in schedules:
        schedule_doc = frappe.get_doc("Lease Contract Schedule", sched.name)
        invoiced = 0
        not_invoiced = 0
        paid_periods = 0
        updated = False

        # Update invoice_status in memory
        for row in schedule_doc.invoice:
            invoice_number = getattr(row, "invoice_number", None)
            if invoice_number and invoice_number in invoice_dict:
                row.invoice_status = invoice_dict[invoice_number]
                updated = True

            if row.invoice_number:
                invoiced += 1
                if row.invoice_status == "Paid":
                    paid_periods += 1
            else:
                not_invoiced += 1

        # Update totals
        schedule_doc.number_of_invoiced_periods = invoiced
        schedule_doc.number_of_non_invoiced_periods = not_invoiced
        schedule_doc.total_paid_peroid = paid_periods

        # Save only if there are changes
        if updated:
            schedule_doc.save(ignore_permissions=True)
            frappe.logger().info(f"Updated status for schedule {sched.name}")
