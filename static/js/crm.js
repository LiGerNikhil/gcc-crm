/**
 * GCC CRM - Main JavaScript
 * Enterprise Banking CRM System
 */

document.addEventListener('DOMContentLoaded', function() {

    // ─── Sidebar Toggle (Mobile) ─────────────────────────────────
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebar');

    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function(e) {
            e.preventDefault();
            sidebar.classList.toggle('show');

            // Create overlay on mobile
            const existingOverlay = document.querySelector('.sidebar-overlay');
            if (sidebar.classList.contains('show')) {
                if (!existingOverlay) {
                    const overlay = document.createElement('div');
                    overlay.className = 'sidebar-overlay';
                    overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.4);z-index:999;';
                    overlay.addEventListener('click', function() {
                        sidebar.classList.remove('show');
                        this.remove();
                    });
                    document.body.appendChild(overlay);
                }
            } else {
                if (existingOverlay) existingOverlay.remove();
            }
        });
    }

    // ─── Upload Zone Drag & Drop ─────────────────────────────────
    document.querySelectorAll('.upload-zone').forEach(zone => {
        const fileInput = zone.querySelector('input[type="file"]');

        zone.addEventListener('click', function() {
            if (fileInput) fileInput.click();
        });

        if (fileInput) {
            fileInput.addEventListener('change', function() {
                if (this.files.length) {
                    updateUploadZone(zone, this.files[0].name);
                }
            });
        }

        zone.addEventListener('dragover', function(e) {
            e.preventDefault();
            this.classList.add('dragover');
        });

        zone.addEventListener('dragleave', function() {
            this.classList.remove('dragover');
        });

        zone.addEventListener('drop', function(e) {
            e.preventDefault();
            this.classList.remove('dragover');
            if (e.dataTransfer.files.length && fileInput) {
                fileInput.files = e.dataTransfer.files;
                updateUploadZone(this, e.dataTransfer.files[0].name);
            }
        });
    });

    function updateUploadZone(zone, fileName) {
        const icon = zone.querySelector('.upload-icon');
        const title = zone.querySelector('h6');
        const desc = zone.querySelector('p');
        if (icon) icon.className = 'upload-icon bi bi-check-circle text-success';
        if (title) title.textContent = fileName;
        if (desc) desc.textContent = 'File selected. Click "Upload" to proceed.';
    }

    // ─── Auto-close alerts ──────────────────────────────────────
    document.querySelectorAll('.alert-dismissible').forEach(alert => {
        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getInstance(alert);
            if (bsAlert) bsAlert.close();
        }, 5000);
    });

    // ─── Select All checkbox ────────────────────────────────────
    const selectAll = document.getElementById('selectAll');
    if (selectAll) {
        selectAll.addEventListener('change', function() {
            document.querySelectorAll('.row-select').forEach(cb => {
                cb.checked = this.checked;
            });
        });
    }

    // ─── Tooltips ───────────────────────────────────────────────
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(el) {
        return new bootstrap.Tooltip(el);
    });

});
