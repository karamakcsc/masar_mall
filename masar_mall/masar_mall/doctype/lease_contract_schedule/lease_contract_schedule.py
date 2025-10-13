# Copyright (c) 2025, KCSC and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class LeaseContractSchedule(Document):
    def on_submit(self):
        self.update_invoiced_period_counts()

    def update_invoiced_period_counts(self):
        invoiced_periods = 0
        non_invoiced_periods = 0

        for row in self.invoice:
            if row.invoice_number:
                invoiced_periods += 1
            else:
                non_invoiced_periods += 1

        frappe.db.set_value(self.doctype, self.name, "number_of_invoiced_periods", invoiced_periods)
        frappe.db.set_value(self.doctype, self.name, "number_of_non_invoiced_periods", non_invoiced_periods)
        # frappe.db.commit()
