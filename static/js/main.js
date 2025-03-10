document.addEventListener('DOMContentLoaded', function() {
    // Toggle password visibility
    const togglePasswordButtons = document.querySelectorAll('.toggle-password');
    togglePasswordButtons.forEach(button => {
        button.addEventListener('click', function() {
            const input = document.getElementById(this.getAttribute('data-target'));
            const type = input.getAttribute('type') === 'password' ? 'text' : 'password';
            input.setAttribute('type', type);
            
            // Update icon
            const icon = this.querySelector('i');
            if (type === 'text') {
                icon.classList.remove('bi-eye');
                icon.classList.add('bi-eye-slash');
            } else {
                icon.classList.remove('bi-eye-slash');
                icon.classList.add('bi-eye');
            }
        });
    });
    
    // Run script button handling
    const runButtons = document.querySelectorAll('.run-script');
    runButtons.forEach(button => {
        button.addEventListener('click', function() {
            const accountId = this.getAttribute('data-account-id');
            const resultContainer = document.getElementById(`result-${accountId}`);
            const spinner = this.querySelector('.spinner-border');
            const buttonText = this.querySelector('.button-text');
            
            // Show spinner
            spinner.classList.remove('d-none');
            buttonText.textContent = 'Ejecutando...';
            this.disabled = true;
            resultContainer.innerHTML = '<div class="alert alert-info">Procesando solicitud...</div>';
            
            // Make AJAX request
            fetch(`/run/${accountId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            })
            .then(response => response.json())
            .then(data => {
                // Hide spinner
                spinner.classList.add('d-none');
                buttonText.textContent = 'Ejecutar';
                this.disabled = false;
                
                // Display result
                let resultHTML = '';
                if (data.status === 'success') {
                    resultHTML = `<div class="alert alert-success">
                        <h5>Ejecutado correctamente</h5>
                        <hr>
                        <ul class="list-unstyled">`;
                        
                    if (data.results && data.results.length > 0) {
                        data.results.forEach(result => {
                            resultHTML += `<li>${result}</li>`;
                        });
                    } else {
                        resultHTML += `<li>${data.message}</li>`;
                    }
                    
                    resultHTML += `</ul></div>`;
                } else {
                    resultHTML = `<div class="alert alert-danger">
                        <h5>Error</h5>
                        <hr>
                        <p>${data.message}</p>
                    </div>`;
                }
                
                resultContainer.innerHTML = resultHTML;
                
                // Auto refresh after successful execution
                if (data.status === 'success') {
                    setTimeout(() => {
                        window.location.reload();
                    }, 5000);
                }
            })
            .catch(error => {
                // Hide spinner
                spinner.classList.add('d-none');
                buttonText.textContent = 'Ejecutar';
                this.disabled = false;
                
                // Display error
                resultContainer.innerHTML = `<div class="alert alert-danger">
                    <h5>Error de conexión</h5>
                    <hr>
                    <p>${error.message}</p>
                </div>`;
            });
        });
    });
    
    // Initialize scheduleTimes inputs
    const scheduleToggles = document.querySelectorAll('.schedule-toggle');
    scheduleToggles.forEach(toggle => {
        toggle.addEventListener('change', function() {
            const timeInput = document.getElementById(this.getAttribute('data-target'));
            timeInput.disabled = !this.checked;
        });
        
        // Set initial state
        const timeInput = document.getElementById(toggle.getAttribute('data-target'));
        timeInput.disabled = !toggle.checked;
    });
    
    // Initialize account deletion confirmation
    const deleteButtons = document.querySelectorAll('.delete-account');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('¿Estás seguro de que deseas eliminar esta cuenta? Esta acción no se puede deshacer.')) {
                e.preventDefault();
            }
        });
    });
    
    // Initialize tooltips
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    
    // Chart initialization if exists
    const chartCanvas = document.getElementById('publicationChart');
    if (chartCanvas) {
        const ctx = chartCanvas.getContext('2d');
        
        // Get data from data attributes
        const labels = JSON.parse(chartCanvas.getAttribute('data-labels'));
        const successData = JSON.parse(chartCanvas.getAttribute('data-success'));
        const errorData = JSON.parse(chartCanvas.getAttribute('data-error'));
        
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Publicaciones exitosas',
                        data: successData,
                        backgroundColor: 'rgba(75, 192, 192, 0.7)',
                        borderColor: 'rgba(75, 192, 192, 1)',
                        borderWidth: 1
                    },
                    {
                        label: 'Errores',
                        data: errorData,
                        backgroundColor: 'rgba(255, 99, 132, 0.7)',
                        borderColor: 'rgba(255, 99, 132, 1)',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: true,
                        text: 'Estadísticas de publicaciones'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            precision: 0
                        }
                    }
                }
            }
        });
    }
});
