document.addEventListener('DOMContentLoaded', function() {
    const filterPanel = document.getElementById('changelist-filter');
    if (!filterPanel) return;

    // Create toggle button
    const btn = document.createElement('div');
    btn.id = 'filter-toggle-btn';
    btn.innerHTML = '<i class="fa-solid fa-filter"></i> Filters';
    document.body.appendChild(btn);

    // Toggle functionality
    btn.addEventListener('click', function() {
        filterPanel.classList.toggle('active');
        btn.classList.toggle('active');
    });

    // Handle data layout
    const changelist = document.getElementById('changelist');
    if (changelist) {
        changelist.classList.add('filtered'); // remove right margin
    }
});
