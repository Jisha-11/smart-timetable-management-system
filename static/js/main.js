// Load notifications on page load
document.addEventListener('DOMContentLoaded', function() {
    loadNotifications();
});

// Function to load notifications
function loadNotifications() {
    const notificationsDiv = document.getElementById('notifications');
    
    if (!notificationsDiv) return;
    
    fetch('/get-notifications')
        .then(response => response.json())
        .then(data => {
            if (data.length === 0) {
                notificationsDiv.innerHTML = '<p style="color: #999;">No new notifications</p>';
                return;
            }
            
            let html = '';
            data.forEach(notification => {
                const date = new Date(notification.timestamp).toLocaleString();
                html += `
                    <div class="notification-item">
                        <h4>${notification.title}</h4>
                        <p>${notification.message}</p>
                        <small>${date}</small>
                    </div>
                `;
            });
            
            notificationsDiv.innerHTML = html;
        })
        .catch(error => {
            console.error('Error loading notifications:', error);
        });
}