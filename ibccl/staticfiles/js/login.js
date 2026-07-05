function initializeTabId() {
            let tabId = sessionStorage.getItem('tab_id');
            if (!tabId) {
                tabId = Math.random().toString(36).substring(2, 10);
                sessionStorage.setItem('tab_id', tabId);
            }

            const currentUrl = new URL(window.location.href);
            if (!currentUrl.searchParams.has('tab_id')) {
                currentUrl.searchParams.set('tab_id', tabId);
                window.history.replaceState(null, '', currentUrl.toString());
            }

            const hiddenTabId = document.getElementById('tabIdField');
            if (hiddenTabId) {
                hiddenTabId.value = currentUrl.searchParams.get('tab_id') || tabId;
            }

            document.querySelectorAll('a[href]').forEach(link => {
                const href = link.getAttribute('href');
                if (!href || href.startsWith('#') || href.startsWith('javascript:')) return;
                try {
                    const url = new URL(link.href, window.location.origin);
                    if (!url.searchParams.has('tab_id') && url.origin === window.location.origin) {
                        url.searchParams.set('tab_id', tabId);
                        link.href = url.toString();
                    }
                } catch (e) {
                    // ignore invalid URLs
                }
            });
        }

        function togglePassword() {
            const passwordInput = document.getElementById('password-input');
            const toggleIcon = document.getElementById('toggle-icon');

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

        document.addEventListener('DOMContentLoaded', function () {
            initializeTabId();
        });

        // Auto-hide messages after 5 seconds
        setTimeout(() => {
            const alerts = document.querySelectorAll('[class*="bg-red-50"]');
            alerts.forEach(alert => {
                alert.style.transition = 'opacity 0.3s ease';
                alert.style.opacity = '0';
                setTimeout(() => alert.remove(), 300);
            });
        }, 5000);