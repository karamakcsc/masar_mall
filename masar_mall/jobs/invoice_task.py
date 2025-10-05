import frappe
from frappe.utils import getdate, nowdate



def update_lease_schedule_status_from_invoice():
    """Update Lease Contract Schedule child table with status from Sales Invoice if invoice date <= today"""
    today = getdate(nowdate())

    # Only use fields that exist in Sales Invoice
    invoices = frappe.get_all(
        "Sales Invoice",
        filters={"posting_date": ["<=", today]},
        fields=["name", "status"],  # Removed 'lease_contract'
        ignore_permissions=True
    )

    if not invoices:
        frappe.logger().info("No Sales Invoices found for today or earlier.")
        return

    for inv in invoices:
        # Find all Lease Contract Schedules where any child row has invoice_number == inv.name
        schedules = frappe.get_all(
            "Lease Contract Schedule",
            filters=[{"docstatus": 1}],  # Only submitted schedules
            fields=["name"]
        )

        for sched in schedules:
            schedule_doc = frappe.get_doc("Lease Contract Schedule", sched.name)
            updated = False
            for row in schedule_doc.invoice:
                if getattr(row, "invoice_number", None) == inv.name:
                    row.invoice_status = inv.status
                    updated = True
            if updated:
                schedule_doc.save(ignore_permissions=True)
                frappe.logger().info(f"Updated status for schedule {sched.name} from invoice {inv.name}")



