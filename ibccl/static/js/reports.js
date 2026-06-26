 (function () {
        const isDark = document.documentElement.classList.contains('dark');
        const gridColor = isDark ? 'rgba(255,255,255,.08)' : 'rgba(0,0,0,.06)';
        const labelColor = isDark ? '#94a3b8' : '#6b7280';

        /* Daily activity line/bar chart */
        const labels = {{ chart_labels_json| safe
    }};
    const approved = {{ chart_approved_json| safe }};
    const pending = {{ chart_pending_json| safe }};
    const rejected = {{ chart_rejected_json| safe }};

    const dailyCtx = document.getElementById('dailyChart');
    if (dailyCtx) {
        new Chart(dailyCtx, {
            type: 'bar',
            data: {
                labels,
                datasets: [
                    {
                        label: 'Approved',
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

    /* Category doughnut */
    const catLabels = {{ cat_labels_json| safe }};
    const catValues = {{ cat_values_json| safe }};
    const palette = ['#4f46e5', '#7c3aed', '#059669', '#d97706', '#dc2626',
        '#0891b2', '#c026d3', '#16a34a', '#ea580c', '#6366f1'];

    const catCtx = document.getElementById('catChart');
    if (catCtx && catValues.length > 0) {
        new Chart(catCtx, {
            type: 'doughnut',
            data: {
                labels: catLabels,
                datasets: [{
                    data: catValues,
                    backgroundColor: palette.slice(0, catValues.length),
                    borderColor: isDark ? '#1e1b3a' : '#fff',
                    borderWidth: 2,
                    hoverOffset: 6,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '62%',
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: ctx => ` ${ctx.label}: ${ctx.parsed} units`
                        }
                    }
                }
            }
        });

        // Custom legend
        const legend = document.getElementById('cat-legend');
        catLabels.forEach((lbl, i) => {
            legend.innerHTML += `
                <div style="display:flex;align-items:center;gap:.4rem;font-size:.72rem;">
                    <span style="width:10px;height:10px;border-radius:2px;background:${palette[i]};flex-shrink:0;"></span>
                    <span style="color:${labelColor};">${lbl}</span>
                    <span style="margin-left:auto;font-weight:700;color:#4f46e5;">${catValues[i]}</span>
                </div>`;
        });
    } else if (catCtx) {
        catCtx.closest('div').innerHTML = '<p style="text-align:center;color:#9ca3af;padding:3rem 0;font-size:.85rem;">No approved requests in period</p>';
    }
}) ();