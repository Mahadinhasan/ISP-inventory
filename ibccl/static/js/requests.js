document.addEventListener('DOMContentLoaded', () => {
        const selects = document.querySelectorAll('select');
        selects.forEach(s => {
            s.classList.add('w-full', 'border-gray-300', 'rounded-md', 'shadow-sm', 'focus:ring-indigo-500', 'focus:border-indigo-500', 'border', 'p-2');
        });
    });

    function openAdminModal(id, note, quantity) {
        document.getElementById('adminReqId').value = id;
        document.getElementById('adminNote').value = note;
        document.getElementById('adminQuantity').value = quantity;
        document.getElementById('adminModal').classList.remove('hidden');
    }

    function openReceivedByModal(id) {
        document.getElementById('receivedByReqId').value = id;
        document.getElementById('receivedByText').value = '';
        document.getElementById('receivedByModal').classList.remove('hidden');
    }

    function openPassOnModal(id) {
        document.getElementById('passOnReqId').value = id;
        document.getElementById('passOnText').value = '';
        document.getElementById('passOnModal').classList.remove('hidden');
    }

    // Handle pass_on form submission via AJAX
    document.getElementById('passOnForm').addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = new FormData(this);
        let fetchUrl = '{% url "requests" %}';
        const tabId = sessionStorage.getItem('tab_id');
        if (tabId) {
            fetchUrl += `?tab_id=${tabId}`;
            formData.append('tab_id', tabId);
        }

        fetch(fetchUrl, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': formData.get('csrfmiddlewaretoken')
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Dispatch information saved successfully!');
                document.getElementById('passOnModal').classList.add('hidden');
                location.reload();
            } else {
                alert('Error: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while saving. Please try again.');
        });
    });

    // Handle received_by form submission via AJAX
    document.getElementById('receivedByForm').addEventListener('submit', function(e) {
        e.preventDefault();
        
        const formData = new FormData(this);
        
        let fetchUrl = '{% url "requests" %}';
        const tabId = sessionStorage.getItem('tab_id');
        if (tabId) {
            fetchUrl += `?tab_id=${tabId}`;
            formData.append('tab_id', tabId);
        }

        fetch(fetchUrl, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': formData.get('csrfmiddlewaretoken')
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Receipt information saved successfully!');
                document.getElementById('receivedByModal').classList.add('hidden');
                location.reload();
            } else {
                alert('Error: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while saving. Please try again.');
        });
    });

    function openRequestModal(type) {
        const modal = document.getElementById('requestModal');
        const typeInput = document.getElementById('requestType');
        const modalTitle = document.getElementById('modalTitle');
        const modalSubtitle = document.getElementById('modalSubtitle');
        const typeIndicator = document.getElementById('typeIndicator');
        const typeText = document.getElementById('typeText');
        const submitBtn = document.getElementById('submitBtn');
        
        typeInput.value = type;
        
        if (type === 'Advance') {
            modalTitle.innerHTML = '<i class="fas fa-star mr-2 text-indigo-600"></i> Advance Materials';
            modalSubtitle.textContent = 'Submit an advance material request';
            typeIndicator.classList.remove('hidden');
            typeIndicator.className = 'bg-indigo-50 p-3 rounded-lg mb-4';
            typeIndicator.querySelector('p').className = 'text-xs font-medium text-indigo-800';
            typeText.textContent = 'Advance Request';
            submitBtn.className = 'px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition font-medium shadow-md';
        } else {
            modalTitle.innerHTML = '<i class="fas fa-paper-plane mr-2 text-blue-600"></i> Request Material';
            modalSubtitle.textContent = 'Submit a regular material request';
            typeIndicator.classList.remove('hidden');
            typeIndicator.className = 'bg-blue-50 p-3 rounded-lg mb-4';
            typeIndicator.querySelector('p').className = 'text-xs font-medium text-blue-800';
            typeText.textContent = 'Regular Request';
            submitBtn.className = 'px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium shadow-md';
        }
        
        modal.classList.remove('hidden');
    }

    // Close on outside click
    window.onclick = function (event) {
        if (event.target.id === 'requestModal') {
            document.getElementById('requestModal').classList.add('hidden');
        }
        if (event.target.id === 'passOnModal') {
            document.getElementById('passOnModal').classList.add('hidden');
        }
    }