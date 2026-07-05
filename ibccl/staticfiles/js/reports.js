 (function () {
        const isDark = document.documentElement.classList.contains('dark');
        const gridColor = isDark ? 'rgba(255,255,255,.08)' : 'rgba(0,0,0,.06)';
        const labelColor = isDark ? '#94a3b8' : '#6b7280';

        /* Daily Used Materials activity chart (UsedMaterial) */
        const labels = (window.REPORTS_DATA && window.REPORTS_DATA.used_chart_labels) || [];
    const approved = (window.REPORTS_DATA && window.REPORTS_DATA.used_chart_accepted) || [];
    const pending = (window.REPORTS_DATA && window.REPORTS_DATA.used_chart_pending) || [];
    const rejected = (window.REPORTS_DATA && window.REPORTS_DATA.used_chart_rejected) || [];

    const dailyCtx = document.getElementById('dailyChart');
    if (dailyCtx) {
        new Chart(dailyCtx, {
            type: 'bar',
            data: {
                labels,
                datasets: [
                    {
                        label: 'Accepted',
                        data: approved,
                        backgroundColor: 'rgba(16,185,129,.75)',
                        borderColor: '#10b981',
                        borderWidth: 1.5,
                        borderRadius: 4,
                    },
                    {
                        label: 'Pending',
                        data: pending,
                        backgroundColor: 'rgba(245,158,11,.7)',
                        borderColor: '#f59e0b',
                        borderWidth: 1.5,
                        borderRadius: 4,
                    },
                    {
                        label: 'Rejected',
                        data: rejected,
                        backgroundColor: 'rgba(239,68,68,.65)',
                        borderColor: '#ef4444',
                        borderWidth: 1.5,
                        borderRadius: 4,
                    },
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'top', labels: { color: labelColor, font: { size: 11 } } },
                    tooltip: { mode: 'index', intersect: false },
                },
                scales: {
                    x: {
                        stacked: false,
                        grid: { color: gridColor },
                        ticks: { color: labelColor, maxRotation: 40 },
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: gridColor },
                        ticks: { color: labelColor, precision: 0 },
                    }
                }
            }
        });
    }

    /* Estimated amount per-branch chart */
    const estLabels = (window.REPORTS_DATA && window.REPORTS_DATA.est_labels) || [];
    const estValues = (window.REPORTS_DATA && window.REPORTS_DATA.est_values) || [];

    const estCtx = document.getElementById('estChart');
    if (estCtx && estValues.length > 0) {
        new Chart(estCtx, {
            type: 'bar',
            data: {
                labels: estLabels,
                datasets: [{
                    label: 'Amount (৳)',
                    data: estValues,
                    backgroundColor: 'rgba(79,70,229,0.85)',
                    borderColor: '#4f46e5',
                    borderWidth: 1.5,
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { callbacks: { label: ctx => `৳ ${ctx.parsed}` } }
                },
                scales: {
                    x: { grid: { color: gridColor }, ticks: { color: labelColor } },
                    y: { grid: { display: false }, ticks: { color: labelColor } }
                }
            }
        });
    } else if (estCtx) {
        estCtx.closest('div').innerHTML = '<p style="text-align:center;color:#9ca3af;padding:3rem 0;font-size:.85rem;">No amount data available for the selected period</p>';
    }

    /* Daily Damaged Materials Activity Chart */
    const dmgLabels = (window.REPORTS_DATA && window.REPORTS_DATA.damaged_chart_labels) || [];
    const dmgValues = (window.REPORTS_DATA && window.REPORTS_DATA.damaged_chart_values) || [];

    const dmgCtx = document.getElementById('dailyDamagedMaterialsChart');
    if (dmgCtx && dmgValues.length > 0) {
        new Chart(dmgCtx, {
            type: 'line',
            data: {
                labels: dmgLabels,
                datasets: [{
                    label: 'Damaged Qty',
                    data: dmgValues,
                    backgroundColor: 'rgba(239, 68, 68, 0.15)',
                    borderColor: '#ef4444',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.35,
                    pointBackgroundColor: '#ef4444',
                    pointBorderColor: '#fff',
                    pointHoverRadius: 6,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { mode: 'index', intersect: false }
                },
                scales: {
                    x: {
                        grid: { color: gridColor },
                        ticks: { color: labelColor }
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: gridColor },
                        ticks: { color: labelColor, precision: 0 }
                    }
                }
            }
        });
    } else if (dmgCtx) {
        dmgCtx.closest('div').innerHTML = '<p style="text-align:center;color:#9ca3af;padding:3rem 0;font-size:.85rem;">No damaged materials data available in this period</p>';
    }
}) ();