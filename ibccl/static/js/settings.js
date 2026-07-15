// JAVASCRIPT SYSTEM ENGINE CONTROLLERS    

//Create Modal Actions
function openCreateModal() {
    document.getElementById('createModal').classList.remove('hidden');
}
function closeCreateModal() {
    document.getElementById('createModal').classList.add('hidden');
}

//Edit Modal Actions
function openEditModal(id, username, email, firstName, lastName, role, phone, address, city, zipCode, isActive) {
    document.getElementById('edit_user_id').value = id;
    document.getElementById('edit_username').value = username;
    document.getElementById('edit_email').value = email;
    document.getElementById('edit_first_name').value = firstName;
    document.getElementById('edit_last_name').value = lastName;
    document.getElementById('edit_role').value = role;
    document.getElementById('edit_phone').value = phone;
    document.getElementById('edit_address').value = address;
    document.getElementById('edit_city').value = city;
    document.getElementById('edit_zip_code').value = zipCode;
    document.getElementById('edit_is_active').checked = isActive;
    document.getElementById('editModal').classList.remove('hidden');
}
function closeEditModal() {
    document.getElementById('editModal').classList.add('hidden');
}

//Delete Modal Actions
function openDeleteModal(id, username) {
    document.getElementById('delete_user_id').value = id;
    document.getElementById('delete_username_display').textContent = username;
    document.getElementById('deleteModal').classList.remove('hidden');
}
function closeDeleteModal() {
    document.getElementById('deleteModal').classList.add('hidden');
}

//Tab Switching Actions
function switchSettingsTab(tab, isInitialLoad = false) {
    // Save active tab selection to sessionStorage
    sessionStorage.setItem('active_settings_tab', tab);
    
    const tabs = {
        'users': { tabEl: 'usersTab', btnEl: 'btn-users' },
        'backup': { tabEl: 'backupTab', btnEl: 'btn-backup' },
        'notifications': { tabEl: 'notificationTab', btnEl: 'btn-notifications' },
        'logs': { tabEl: 'logTab', btnEl: 'btn-logs' },
        'oauth': { tabEl: 'oauthSettingsTab', btnEl: 'btn-oauth' }
    };

    const sidebar = document.getElementById('settings-sidebar');
    const content = document.getElementById('settings-content');
    
    // On mobile view (window width < 1024px)
    if (window.innerWidth < 1024) {
        const urlParams = new URLSearchParams(window.location.search);
        const hasUrlTab = urlParams.has('tab');
        
        if (isInitialLoad && !hasUrlTab) {
            // Initially, show only the menu if no specific tab is requested
            if (sidebar) {
                sidebar.classList.remove('hidden');
                sidebar.classList.add('block');
            }
            if (content) {
                content.classList.add('hidden');
                content.classList.remove('block');
            }
        } else {
            // When a feature clicked or specific tab is loaded, show content and hide menu list
            if (sidebar) {
                sidebar.classList.add('hidden');
                sidebar.classList.remove('block');
            }
            if (content) {
                content.classList.remove('hidden');
                content.classList.add('block');
            }
        }
    }

    for (const [key, config] of Object.entries(tabs)) {
        const tabEl = document.getElementById(config.tabEl);
        const btnEl = document.getElementById(config.btnEl);
        
        if (tabEl) {
            if (key === tab) {
                tabEl.classList.remove('hidden');
            } else {
                tabEl.classList.add('hidden');
            }
        }
        
        if (btnEl) {
            if (key === tab) {
                btnEl.className = "w-full text-left px-4 py-2.5 rounded-xl font-semibold text-sm transition-all duration-300 active:scale-95 flex items-center bg-gradient-to-r from-indigo-600 to-violet-600 text-white shadow-lg shadow-indigo-200 dark:shadow-indigo-900/40 border border-transparent";
            } else {
                btnEl.className = "w-full text-left px-4 py-2.5 rounded-xl font-semibold text-sm transition-all duration-300 active:scale-95 flex items-center bg-transparent text-gray-600 dark:text-gray-300 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 hover:text-indigo-700 dark:hover:text-indigo-300";
            }
        }
    }
}

//Mobile Back to Menu Action
function goBackToMenu() {
    const sidebar = document.getElementById('settings-sidebar');
    const content = document.getElementById('settings-content');
    
    if (sidebar) {
        sidebar.classList.remove('hidden');
        sidebar.classList.add('block');
    }
    if (content) {
        content.classList.add('hidden');
        content.classList.remove('block');
    }
}

//Toggle Restore Input Method
function toggleRestoreInput(restoreType) {
    const fileSection = document.getElementById('file-upload-section');
    const historySection = document.getElementById('history-section');
    
    if (restoreType === 'file') {
        fileSection.classList.remove('hidden');
        historySection.classList.add('hidden');
    } else {
        fileSection.classList.add('hidden');
        historySection.classList.remove('hidden');
    }
}

//Toggle Password Visibility
function togglePassword(inputId, iconId) {
    const passwordInput = document.getElementById(inputId);
    const toggleIcon = document.getElementById(iconId);
    
    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        toggleIcon.classList.remove('fa-eye');
        toggleIcon.classList.add('fa-eye-slash');
    } else {
        passwordInput.type = 'password';
        toggleIcon.classList.remove('fa-eye-slash');
        toggleIcon.classList.add('fa-eye');
    }
}

//Real-time Password Strength Checkers
document.addEventListener('DOMContentLoaded', function() {
    // Check URL query parameters for active tab
    const urlParams = new URLSearchParams(window.location.search);
    const urlTab = urlParams.get('tab');
    
    // If not in URL, check sessionStorage
    const storedTab = sessionStorage.getItem('active_settings_tab');
    
    const defaultTab = urlTab || storedTab || 'users';
    
    // Initialize default active tab styling
    switchSettingsTab(defaultTab, true);

    const createPass = document.getElementById('create-password-input');
    const editPass = document.getElementById('edit-password-input');

    if (createPass) {
        createPass.addEventListener('input', () => validatePasswordUI(createPass.value, 'create'));
    }
    if (editPass) {
        editPass.addEventListener('input', () => validatePasswordUI(editPass.value, 'edit'));
    }
});

function validatePasswordUI(value, prefix) {
    const requirements = {
        length: value.length >= 8,
        upper: /[A-Z]/.test(value),
        lower: /[a-z]/.test(value),
        number: /[0-9]/.test(value)
    };

    for (const [req, met] of Object.entries(requirements)) {
        const el = document.getElementById(`${prefix}-req-${req}`);
        if (el) {
            const icon = el.querySelector('i');
            if (met) {
                el.classList.remove('text-red-500');
                el.classList.add('text-green-600');
                icon.classList.remove('fa-times-circle');
                icon.classList.add('fa-check-circle');
            } else {
                el.classList.remove('text-green-600');
                el.classList.add('text-red-500');
                icon.classList.remove('fa-check-circle');
                icon.classList.add('fa-times-circle');
            }
        }
    }
}

// Restore source toggle (Settings Backup Tab)
function toggleSettingsRestoreInput(value) {
    const fileSection = document.getElementById('settings-file-section');
    const historySection = document.getElementById('settings-history-section');
    if (!fileSection || !historySection) return;
    if (value === 'history') {
        fileSection.classList.add('hidden');
        historySection.classList.remove('hidden');
    } else {
        fileSection.classList.remove('hidden');
        historySection.classList.add('hidden');
    }
}

// Restore source toggle (Dedicated Backup & Restore Page)
function toggleRestoreInput(value) {
    const fileSection = document.getElementById('file-upload-section');
    const historySection = document.getElementById('history-section');
    if (!fileSection || !historySection) return;
    if (value === 'history') {
        fileSection.classList.add('hidden');
        historySection.classList.remove('hidden');
    } else {
        fileSection.classList.remove('hidden');
        historySection.classList.add('hidden');
    }
}