// Copyright (c) 2025, KCSC and contributors
// For license information, please see license.txt


frappe.ui.form.on('Property', {
    location(frm) {
        // If no location but lat/lng exist, set map to those coordinates
        if (!frm.doc.location && frm.doc.latitude && frm.doc.longitude) {
            frm.fields_dict.location.map.setView([frm.doc.latitude, frm.doc.longitude], 13);
        } else {
            // Otherwise, store map center as lat/lng
            let center = frm.fields_dict.location.map.getCenter();
            frm.doc.latitude = center.lat;
            frm.doc.longitude = center.lng;
        }
    },

    location: function(frm) {
        // Whenever location is changed, update lat/lng fields
        let center = frm.fields_dict.location.map.getCenter();
        frm.doc.latitude = center.lat;
        frm.doc.longitude = center.lng;

        // Reverse geocode immediately
        fetch(`https://nominatim.openstreetmap.org/reverse?lat=${frm.doc.latitude}&lon=${frm.doc.longitude}&format=json`)
            .then(response => response.json())
            .then(data => {
                if (data && data.display_name) {
                    frm.set_value('address', data.display_name);
                } else {
                    frappe.msgprint(__('Address not found for this location.'));
                }
            })
            .catch(err => {
                console.error(err);
                frappe.msgprint(__('Error getting address.'));
            });
    },

    validate(frm) {
        // Also reverse geocode on save in case the user skipped location change
        if (frm.doc.latitude && frm.doc.longitude) {
            fetch(`https://nominatim.openstreetmap.org/reverse?lat=${frm.doc.latitude}&lon=${frm.doc.longitude}&format=json`)
                .then(response => response.json())
                .then(data => {
                    if (data && data.display_name) {
                        frm.set_value('address', data.display_name);
                    } else {
                        frappe.msgprint(__('Address not found for this location.'));
                    }
                })
                .catch(err => {
                    console.error(err);
                    frappe.msgprint(__('Error getting address.'));
                });
        }
    }
});
