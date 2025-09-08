# Copyright (c) 2025, KCSC and contributors
# For license information, please see license.txt

import frappe
from dateutil.relativedelta import relativedelta
from frappe.utils import add_months, get_last_day, getdate
from frappe.model.document import Document


class LeaseContract(Document):
    def on_submit(self):
        self.add_into_child()
        self.create_log()
        frappe.msgprint("Lease Contract Schedule has been created successfully.")

    def validate(self):
        self.validate_dates()
        self.calculate_period_in_months()
        self.check_pay_type_against_period()  # <-- pay_type validation added

    def validate_dates(self):
        if self.lease_start and self.lease_end:
            if self.lease_start > self.lease_end:
                frappe.throw("Lease start date cannot be after lease end date.")
        elif not self.lease_start or not self.lease_end:
            frappe.throw("Both lease start and lease end dates must be provided.")
        else:
            frappe.msgprint("Lease dates are valid.")

        # # Normalize lease_start to first of month
        # if self.lease_start:
        #     start_date = frappe.utils.getdate(self.lease_start)
        #     self.lease_start = start_date.replace(day=1)

        # # Normalize lease_end to last of month
        # if self.lease_end:
        #     end_date = frappe.utils.getdate(self.lease_end)
        #     if end_date.month == 12:
        #         next_month = end_date.replace(year=end_date.year+1, month=1, day=1)
        #     else:
        #         next_month = end_date.replace(month=end_date.month+1, day=1)
        #     self.lease_end = next_month - relativedelta(days=1)

    def calculate_period_in_months(self):
        if hasattr(self, 'lease_start') and hasattr(self, 'lease_end') and self.lease_start and self.lease_end:
            start_date = frappe.utils.getdate(self.lease_start)
            end_date = frappe.utils.getdate(self.lease_end)
            delta = relativedelta(end_date, start_date)
            lease_months = delta.years * 12 + delta.months + (1 if delta.days > 0 else 0)
            frappe.msgprint(str(lease_months) + " months in lease period")
            allowance_months = int(getattr(self, 'allowance_period', 0) or 0)
            if getattr(self, 'in_period', False):
                # Free months are part of period
                self.period_in_months = lease_months
                self.paid_months = max(0, lease_months - allowance_months)
            else:
                # Free months are outside period
                self.period_in_months = lease_months + allowance_months
                self.paid_months = lease_months

    def check_pay_type_against_period(self):
        """Validate that selected pay_type fits within lease period"""
        pay_type_map = {
            "1 month": 1,
            "2 month": 2,
            "3 month": 3,
            "6 month": 6,
            "1 year": 12
        }

        interval = pay_type_map.get(self.pay_type, 1)
        period = getattr(self, 'period_in_months', 0)

        if interval > period:
            frappe.throw(
                f"Payment type '{self.pay_type}' is longer than the lease period of {period} month(s). Please choose a smaller payment type."
            )

    def add_into_child(self):
        new_doc = frappe.new_doc("Lease Contract Schedule")
        new_doc.lease_contract = self.name

        # --- setup & helpers ---
        start_date = getdate(self.lease_start)
        allowance_months = int(getattr(self, 'allowance_period', 0) or 0)
        in_period = getattr(self, 'in_period', False)

        pay_type_map = {
            "1 month": 1,
            "2 month": 2,
            "3 month": 3,
            "4 month": 4,
            "6 month": 6,
            "1 year": 12
        }
        interval = pay_type_map.get(getattr(self, "pay_type", "1 month"), 1)

        # Determine tax flag once (used for paid intervals)
        def get_tax_flag():
            if getattr(self, "include_vat", False) and getattr(self, "tax_template", None):
                try:
                    tax_doc = frappe.get_doc("Sales Taxes and Charges Template", self.tax_template)
                    return "Taxable" if getattr(tax_doc, "taxes", None) else "Exempt"
                except Exception:
                    frappe.log_error(frappe.get_traceback(), "Failed to get tax template")
                    return "Exempt"
            return "Exempt"

        tax_flag = get_tax_flag()

        # Sum ALL monthly rent elements so we produce ONE invoice per interval
        total_monthly_amount = 0
        for row in (self.rent_details or []):
            total_monthly_amount += float(getattr(row, "amount", 0) or 0)
        total_monthly_amount = float(total_monthly_amount or 0)

        # --- free months ---
        if allowance_months > 0:
            if in_period:
                free_cursor = start_date
                for i in range(allowance_months):
                    period_start = free_cursor
                    period_end = get_last_day(period_start)
                    new_doc.append("invoice", {
                        "lease_start": period_start,
                        "lease_end": period_end,
                        "amount": 0,
                        "rate": 0,
                        "tax": "Exempt",
                        "is_allowance": 1
                    })
                    free_cursor = add_months(period_start, 1)
                paid_start_date = free_cursor
            else:
                free_cursor = add_months(start_date, -allowance_months)
                for i in range(allowance_months):
                    period_start = free_cursor
                    period_end = get_last_day(period_start)
                    new_doc.append("invoice", {
                        "lease_start": period_start,
                        "lease_end": period_end,
                        "amount": 0,
                        "rate": 0,
                        "tax": "Exempt",
                        "is_allowance": 1
                    })
                    free_cursor = add_months(period_start, 1)
                paid_start_date = start_date
        else:
            paid_start_date = start_date

        # --- paid months grouped by pay_type interval ---
        remaining = int(getattr(self, "paid_months", 0) or 0)
        cursor = paid_start_date

        while remaining > 0:
            months_to_process = min(interval, remaining)

            period_start = cursor
            # Default = last day of interval
            period_end = get_last_day(add_months(period_start, months_to_process - 1))

            # --- adjust last invoice to match lease_end ---
            if remaining == months_to_process:  
                period_end = getdate(self.lease_end)

            interval_amount = total_monthly_amount * months_to_process

            new_doc.append("invoice", {
                "lease_start": period_start,
                "lease_end": period_end,
                "amount": interval_amount,
                "rate": 0,
                "tax": tax_flag,
                "is_allowance": 0
            })

            cursor = add_months(period_start, months_to_process)
            remaining -= months_to_process

        new_doc.save(ignore_permissions=True)
        new_doc.submit()
    def create_log(self):
        """Create Lease Contract Log when Lease Contract is submitted"""
        log = frappe.new_doc("Lease Contract Log")
        log.lease_contract = self.name
        log.tenant_lessee = self.tenant_lessee
        log.lease_start = self.lease_start
        log.lease_end = self.lease_end

        # Fill from Lease Contract Details (first row)
        if self.rent_details and len(self.rent_details) > 0:
            rent_row = self.rent_details[0]
            log.rent_item = rent_row.rent_item
            log.floor_unit = rent_row.floor_unit
            log.rate = rent_row.rate
            log.amount = rent_row.amount

        # Fill from Lease Contract Invoice (first row)
        if hasattr(self, "invoice") and self.invoice and len(self.invoice) > 0:
            invoice_row = self.invoice[0]
            log.invoice_start = invoice_row.invoice_start
            log.invoice_end = invoice_row.invoice_end
            log.invoice_number = invoice_row.invoice_number
            log.invoice_statu = invoice_row.invoice_statu
            log.amount = invoice_row.amount  # Overwrites amount if needed

        log.insert(ignore_permissions=True)
        log.submit()

