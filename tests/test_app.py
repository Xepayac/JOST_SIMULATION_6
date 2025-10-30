def test_home_page(client):
    """
    GIVEN a Flask application configured for testing
    WHEN the '/' page is requested (GET)
    THEN check that the response is valid
    """
    response = client.get('/')
    assert response.status_code == 302 # Expect a redirect

    response = client.get('/', follow_redirects=True)
    assert response.status_code == 200
    assert b"New Simulation" in response.data
