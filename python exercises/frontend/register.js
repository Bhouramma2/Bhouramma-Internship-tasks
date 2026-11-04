function register() {
    let username = document.getElementById("name").value;

    if (username.length > 0) {
        alert("Welcome " + username);
    }
    else {
        alert("Name is required!");
    }
}