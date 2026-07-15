# Authentication Flow Documentation

This document describes the JSON Web Token (JWT) issuance, verification, and refresh lifecycle used by the Smart University Management System (SUMS) backend API.

---

## 1. Authentication Credentials & Login

To authenticate a user, the client must send a `POST` request with the user's email and password:

- **Endpoint:** `POST /api/v1/auth/login`
- **Request Type:** URL-encoded Form (`application/x-www-form-urlencoded`)
- **Parameters:**
  - `username`: User's email address
  - `password`: User's password

### Response Envelope:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsIn...",
  "token_type": "bearer"
}
```

---

## 2. Token Configuration & Expiry

- **Access Token:**
  - Expiry: **30 minutes** (configured via `ACCESS_TOKEN_EXPIRE_MINUTES`)
  - Usage: Included in the header of every stateful API request.
- **Refresh Token:**
  - Expiry: **7 days** (configured via `REFRESH_TOKEN_EXPIRE_DAYS`)
  - Usage: Kept securely by the client to obtain new access tokens without requiring re-login.

---

## 3. Authenticating API Requests

For all protected routes, the client must include the access token in the `Authorization` HTTP header:

```http
Authorization: Bearer <access_token>
```

- If the token is missing: `401 Unauthorized` with error code `authentication_error`.
- If the token is expired or signature is invalid: `401 Unauthorized` with error code `authentication_error`.

---

## 4. Token Refresh Lifecycle

When the access token expires (typically after 30 minutes), the client should request a new access token using the refresh token:

- **Endpoint:** `POST /api/v1/auth/refresh`
- **Request Headers:**
  - `Authorization: Bearer <refresh_token>`

### Response Envelope:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsIn...",
  "token_type": "bearer"
}
```

The server verifies the refresh token's signature and expiration, issues a brand new access token (good for another 30 minutes), and optionally returns a new refresh token (refresh rotation).

---

## 5. Logout

To invalidate the session on the client side, discard the stored access and refresh tokens. On the server side, token blacklisting can optionally be implemented in later phases; currently, discarding client-side tokens terminates the session.
