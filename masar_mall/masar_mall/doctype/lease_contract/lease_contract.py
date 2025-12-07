# Copyright (c) 2025, KCSC and contributors
# For license information, please see license.txt

import frappe
from dateutil.relativedelta import relativedelta
from frappe.utils import add_months, get_last_day, getdate, flt, cint, get_first_day, rounded
from frappe.model.document import Document
from masar_mall.utils.create_log import create_log, create_floor_unit_log


class LeaseContract(Document):
    def validate(self):
        self.validate_dates()
        self.validate_allowance_period_selection()
        self.calculate_period_in_months()
        self.check_pay_type_against_period()
        self.validate_renewal_link()
        self.validate_period_details()
        self.validate_rent_totals()
    def on_submit(self):
        frappe.set_value(self.doctype, self.name, "status", "Rent")
        self.create_lease_schedule()
        self.update_floor_unit()
        if self.renewed_from:
            self.renew_lease(self.renewed_from)
        create_log(self)


    def validate_dates(self):
        if self.lease_start and self.lease_end:
            if self.lease_start > self.lease_end:
                frappe.throw("Lease start date cannot be after lease end date.")
        elif not self.lease_start or not self.lease_end:
            frappe.throw("Both lease start and lease end dates must be provided.")

    def validate_allowance_period_selection(self):
        if self.allowance_period and self.allowance_period > 0:
            if not self.in_period and not self.out_period:
                frappe.throw(
                    "You must select either 'Inside the Billing Period' or 'Outside the Billing Period' when Allowance Period is set.",
                    title="Allowance Period Configuration Required"
                )

            if self.in_period and self.out_period:
                frappe.throw(
                    "You cannot select both 'Inside the Billing Period' and 'Outside the Billing Period'. Please select only one.",
                    title="Allowance Period Configuration Required"
                )
                
    def calculate_period_in_months(self):
        if hasattr(self, 'lease_start') and hasattr(self, 'lease_end') and self.lease_start and self.lease_end:
            start_date = getdate(self.lease_start)
            end_date = getdate(self.lease_end)
            delta = relativedelta(end_date, start_date)
            lease_months = delta.years * 12 + delta.months + (1 if delta.days > 0 else 0)

            self.period_in_months = lease_months
                
    def check_pay_type_against_period(self):
        interval = cint(self.billing_frequency)
        period = self.period_in_months

        if interval > period:
            frappe.throw(f"Payment type '{self.billing_frequency}' is longer than the lease period of {period} month(s). Please choose a smaller payment type.")
    
    def validate_renewal_link(self):
        if self.renewed_from:
            if not frappe.db.exists("Lease Contract", self.renewed_from):
                frappe.throw(f"The contract '{self.renewed_from}' does not exist.")
            
            original_status = frappe.db.get_value("Lease Contract", self.renewed_from, "status")
            if original_status != "Renewal":
                frappe.msgprint(
                    f"Warning: The original contract '{self.renewed_from}' status is '{original_status}', not 'Renewal'.",
                    alert=True,
                    indicator="orange"
                )
                
    def validate_period_details(self):
        if self.contract_multi_period:
            if self.period_details:
                for period in self.period_details:
                    if period.from_date >= period.to_date:
                        frappe.throw(f"In period details, 'From Date' must be before 'To Date' for period starting {period.from_date}.")
                    if period.from_date < self.lease_start or period.to_date > self.lease_end:
                        frappe.throw(f"In period details, dates must be within the lease contract dates ({self.lease_start} to {self.lease_end}).")
                total_months = sum(cint(period.month_in_period) for period in self.period_details)
                if total_months != self.period_in_months:
                    frappe.throw("The sum of months in period details must equal the total lease period in months.")

    def validate_rent_totals(self):
        if self.rent_details and self.period_details and self.contract_multi_period:
            rent_details_total = self.total_rent_amount
            period_details_total = sum(p.amount for p in self.period_details) 
            
            if flt(rent_details_total, 2) != flt(period_details_total, 2):
                frappe.throw(f"The Total Rent Amount: {flt(rent_details_total, 2)} does not equal the total in the multi period table: {flt(period_details_total, 2)}.")   
                    
    def create_lease_schedule(self):
        if not self.lease_start or not self.lease_end:
            frappe.throw("Lease start and end dates must be set to create lease schedule")
            
        if not self.period_in_months:
            frappe.throw("Period in months must be set to create lease schedule")
        
        if not self.billing_frequency:
            frappe.throw("Billing frequency must be set to create lease schedule")

        schedule = frappe.new_doc("Lease Contract Schedule")
        schedule.lease_contract = self.name
        schedule.posting_date = frappe.utils.nowdate()
        total_schedule_months = 0

        billing_interval = cint(self.billing_frequency)
        allowance_months = self.allowance_period if self.allowance_period else 0

        if self.contract_multi_period:
            if not self.period_details:
                frappe.throw("Period details are required for multi-period contracts to create lease schedule")

            total_schedule_months = 0
            free_months_applied = False

            if self.out_period and allowance_months > 0:
                first_period_start = getdate(self.period_details[0].from_date)
                self.add_free_months(schedule, first_period_start, allowance_months)
                shift_months = allowance_months
            else:
                shift_months = 0

            for idx, period in enumerate(self.period_details):
                period_start = getdate(period.from_date)
                period_end = getdate(period.to_date)
                months_in_period = cint(period.month_in_period)
                monthly_rent = rounded(flt(period.amount / months_in_period, 6), 6)

                current_start = add_months(period_start, shift_months) if idx == 0 else period_start

                if self.in_period and allowance_months > 0 and not free_months_applied:
                    self.add_free_months(schedule, current_start, allowance_months)
                    current_start = add_months(current_start, allowance_months)
                    free_months_applied = True
                    monthly_rent = rounded(flt(period.amount / (months_in_period - allowance_months), 6), 6)
                paid_period_end = period_end
                if self.in_period and allowance_months > 0 and idx == 0:
                    paid_period_end = add_months(current_start, months_in_period - allowance_months) - relativedelta(days=1)

                self.add_paid_invoices(schedule, current_start, paid_period_end, months_in_period if idx > 0 else months_in_period - (allowance_months if self.in_period else 0), billing_interval, monthly_rent)
                total_schedule_months += months_in_period

            if self.out_period and allowance_months > 0:
                total_schedule_months += allowance_months

            schedule.total_peroid = total_schedule_months
            schedule.insert(ignore_permissions=True)
            schedule.submit()
            frappe.msgprint("Lease Contract Schedule (multi-period) has been created successfully.", alert=True, indicator="green")
            return

        if not self.rent_details:
            frappe.throw("Rent details are required to create lease schedule")

        start_date = getdate(self.lease_start)
        end_date = getdate(self.lease_end)
        total_months = self.period_in_months

        rent_total = sum(rounded(flt(d.amount, 6), 6) for d in self.rent_details if d.rent_space)
        service_total = sum(rounded(flt(d.amount, 6), 6) for d in self.rent_details if not d.rent_space)
        total_rent = rent_total + service_total
        monthly_rent = rounded(flt(total_rent / total_months, 6), 6)
        total_months_with_allowance = total_months
        if self.out_period and allowance_months > 0:
            total_months_with_allowance += allowance_months
        if self.in_period and allowance_months > 0:
            monthly_rent = rounded(flt(total_rent / (total_months - allowance_months), 6), 6)

        schedule.total_peroid = total_months_with_allowance
        current_start = start_date

        if self.in_period and allowance_months > 0:
            self.add_free_months(schedule, current_start, allowance_months)
            current_start = add_months(current_start, allowance_months)
            self.add_paid_invoices(schedule, current_start, end_date, total_months - allowance_months, billing_interval, monthly_rent)
        elif self.out_period and allowance_months > 0:
            self.add_free_months(schedule, current_start, allowance_months)
            current_start = add_months(current_start, allowance_months)
            total_months_with_allowance = total_months + allowance_months
            extended_end_date = add_months(end_date, allowance_months)
            self.add_paid_invoices(schedule, current_start, extended_end_date, total_months, billing_interval, monthly_rent)
        else:
            self.add_paid_invoices(schedule, current_start, end_date, total_months, billing_interval, monthly_rent)

        schedule.insert(ignore_permissions=True)
        schedule.submit()
        frappe.msgprint("Lease Contract Schedule has been created successfully.", alert=True, indicator="green")

    def add_free_months(self, schedule, start_date, num_months):
        current_date = start_date
        
        for i in range(num_months):
            period_start = current_date
            period_end = get_last_day(period_start)
            
            schedule.append("invoice", {
                "lease_start": period_start,
                "lease_end": period_end,
                "amount": 0,
                "is_allowance": 1
            })
            
            current_date = add_months(current_date, 1)

    def add_paid_invoices(self, schedule, start_date, end_date, total_months, billing_interval, monthly_rent):
        if total_months <= 0:
            return
        
        current_date = start_date
        remaining_months = total_months
        
        while remaining_months > 0:
            months_in_invoice = min(billing_interval, remaining_months)
            period_start = current_date
            
            if remaining_months <= billing_interval:
                period_end = end_date
            else:
                period_end = get_last_day(add_months(period_start, months_in_invoice - 1))
            
            invoice_amount = rounded(flt(monthly_rent * months_in_invoice, 6), 6)
            
            schedule.append("invoice", {
                "lease_start": period_start,
                "lease_end": period_end,
                "amount": invoice_amount,
                "is_allowance": 0
            })
            
            current_date = add_months(current_date, months_in_invoice)
            remaining_months -= months_in_invoice
            
    def update_floor_unit(self):
        if self.rent_details:
            for floor in self.rent_details:
                if floor.floor_unit:
                    frappe.db.set_value("Floor Unit", floor.floor_unit, "rent_space", 1)
                    frappe.db.set_value("Floor Unit", floor.floor_unit, "tenant", self.tenant_lessee)
                    try:
                        floor_unit_doc = frappe.get_doc("Floor Unit", floor.floor_unit)
                        create_floor_unit_log(floor_unit_doc)
                    except Exception as e:
                        frappe.throw(f"Error Logging Floor Unit: {e}")
            frappe.db.commit()
            
    def renew_lease(self, renewal_self):
        renewal_doc = frappe.get_doc("Lease Contract", renewal_self)
        frappe.db.set_value(renewal_doc.doctype, renewal_doc.name, "status", "Renewal")
        frappe.db.commit()
        renewal_doc.reload()
        create_log(renewal_doc)
        
        frappe.msgprint("Contract marked for renewal.", alert=True, indicator="blue")

    @frappe.whitelist()
    def terminate_lease(self):
        if self.rent_details:
            for floor in self.rent_details:
                if floor.floor_unit:
                    try:
                        floor_unit_doc = frappe.get_doc("Floor Unit", floor.floor_unit)
                        floor_unit_doc.release_from_lease()
                    except Exception as e:
                        frappe.throw(f"Error Reverse Unit SE: {e}")
            
            frappe.db.set_value(self.doctype, self.name, "status", "Terminated")
            frappe.db.commit()
            
            self.reload()
            create_log(self)
            
            frappe.msgprint("Lease contract terminated successfully.", alert=True, indicator="orange")

    @frappe.whitelist()
    def legal_case(self):
        frappe.db.set_value(self.doctype, self.name, "status", "Legal Case")
        frappe.db.commit()
        

    @frappe.whitelist()
    def generate_schedule_preview(self):
        if not self.lease_start or not self.lease_end:
            frappe.throw("Lease start and end dates must be set to preview lease schedule")
            
        if not self.period_in_months:
            frappe.throw("Period in months must be set to preview lease schedule")
        
        if not self.billing_frequency:
            frappe.throw("Billing frequency must be set to preview lease schedule")

        preview_data = {
            "invoice": [],
            "total_period": 0
        }

        billing_interval = cint(self.billing_frequency)
        allowance_months = self.allowance_period if self.allowance_period else 0

        if self.contract_multi_period:
            if not self.period_details:
                frappe.throw("Period details are required for multi-period contracts to preview lease schedule")

            total_schedule_months = 0
            free_months_applied = False

            if self.out_period and allowance_months > 0:
                first_period_start = getdate(self.period_details[0].from_date)
                self.preview_free_months(preview_data, first_period_start, allowance_months)
                shift_months = allowance_months
            else:
                shift_months = 0

            for idx, period in enumerate(self.period_details):
                period_start = getdate(period.from_date)
                period_end = getdate(period.to_date)
                months_in_period = cint(period.month_in_period)
                monthly_rent = flt(period.amount) / months_in_period

                current_start = add_months(period_start, shift_months) if idx == 0 else period_start

                if self.in_period and allowance_months > 0 and not free_months_applied:
                    self.preview_free_months(preview_data, current_start, allowance_months)
                    current_start = add_months(current_start, allowance_months)
                    free_months_applied = True
                    monthly_rent = flt(period.amount) / (months_in_period - allowance_months)

                paid_period_end = period_end
                if self.in_period and allowance_months > 0 and idx == 0:
                    paid_period_end = add_months(current_start, months_in_period - allowance_months) - relativedelta(days=1)

                self.preview_paid_invoices(preview_data, current_start, paid_period_end, 
                                            months_in_period if idx > 0 else months_in_period - (allowance_months if self.in_period else 0), 
                                            billing_interval, monthly_rent)
                total_schedule_months += months_in_period

            if self.out_period and allowance_months > 0:
                total_schedule_months += allowance_months

            preview_data["total_period"] = total_schedule_months
            return preview_data

        if not self.rent_details:
            frappe.throw("Rent details are required to preview lease schedule")

        start_date = getdate(self.lease_start)
        end_date = getdate(self.lease_end)
        total_months = self.period_in_months

        rent_total = sum(flt(d.amount) for d in self.rent_details if d.rent_space)
        service_total = sum(flt(d.amount) for d in self.rent_details if not d.rent_space)
        total_rent = rent_total + service_total
        monthly_rent = flt(total_rent) / flt(total_months)
        total_months_with_allowance = total_months
        
        if self.out_period and allowance_months > 0:
            total_months_with_allowance += allowance_months
        if self.in_period and allowance_months > 0:
            monthly_rent = flt(total_rent / (total_months - allowance_months))

        preview_data["total_period"] = total_months_with_allowance
        current_start = start_date

        if self.in_period and allowance_months > 0:
            self.preview_free_months(preview_data, current_start, allowance_months)
            current_start = add_months(current_start, allowance_months)
            self.preview_paid_invoices(preview_data, current_start, end_date, total_months - allowance_months, billing_interval, monthly_rent)
        elif self.out_period and allowance_months > 0:
            self.preview_free_months(preview_data, current_start, allowance_months)
            current_start = add_months(current_start, allowance_months)
            total_months_with_allowance = total_months + allowance_months
            extended_end_date = add_months(end_date, allowance_months)
            self.preview_paid_invoices(preview_data, current_start, extended_end_date, total_months, billing_interval, monthly_rent)
        else:
            self.preview_paid_invoices(preview_data, current_start, end_date, total_months, billing_interval, monthly_rent)

        return preview_data

    def preview_free_months(self, preview_data, start_date, num_months):
        current_date = start_date
        
        for i in range(num_months):
            period_start = current_date
            period_end = get_last_day(period_start)
            
            preview_data["invoice"].append({
                "lease_start": str(period_start),
                "lease_end": str(period_end),
                "amount": 0,
                "is_allowance": 1
            })
            
            current_date = add_months(current_date, 1)

    def preview_paid_invoices(self, preview_data, start_date, end_date, total_months, billing_interval, monthly_rent):
        if flt(total_months) <= 0:
            return
        
        current_date = start_date
        remaining_months = flt(total_months)
        
        while remaining_months > 0:
            months_in_invoice = min(billing_interval, remaining_months)
            period_start = current_date
            
            if remaining_months <= billing_interval:
                period_end = end_date
            else:
                period_end = get_last_day(add_months(period_start, months_in_invoice - 1))
            
            invoice_amount = monthly_rent * months_in_invoice
            
            preview_data["invoice"].append({
                "lease_start": str(period_start),
                "lease_end": str(period_end),
                "amount": invoice_amount,
                "is_allowance": 0
            })
            
            current_date = add_months(current_date, months_in_invoice)
            remaining_months -= months_in_invoice