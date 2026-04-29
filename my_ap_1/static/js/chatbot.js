function sendMessage() {
    const message = document.getElementById("user-message").value;
    fetch("/chatbot/", {
        method: "POST",
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: "message=" + encodeURIComponent(message)
    })
    .then(response => response.json())
    .then(data => {
        const chatLog = document.getElementById("chat-log");
        chatLog.innerHTML += "<p><b>You:</b> " + message + "</p>";
        chatLog.innerHTML += "<p><b>Bot:</b> " + data.answer + "</p>";
    });
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            cookie = cookie.trim();
            if (cookie.startsWith(name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
