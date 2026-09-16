def signup(client, email="alex@example.com", password="password123"):
    return client.post(
        "/signup",
        data={"email": email, "password": password},
        follow_redirects=True,
    )


def login(client, email="alex@example.com", password="password123"):
    return client.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=True,
    )
