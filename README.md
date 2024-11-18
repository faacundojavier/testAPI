# README.md

## Users and Roles management API
This application provides endpoints for managing users and roles, including creating, modifying, deleting, and retrieving them. Additionally, it supports assigning and removing roles from users.
The application is containerized using Docker and deployed on Google Cloud, with OAuth configured using GitHub as Identity Provider (IDP).

### Features
-User Management: Create, delete, and retrieve users.
-Role Management: Create, modify, delete, and retrieve roles.
-Role Assignment: Assign and remove roles from users.
-OAuth Integration: Secure authentication using GitHub as the IDP.
-Containerization: The application is packaged in a Docker container for easy deployment.

### Technologies
-Flask: A lightweight WSGI web application framework for Python.
-SQLAlchemy: Python SQL toolkit and Object Relational mapper (ORM) for database management.
-SQLite: Lightweight database used for development.
-Docker: Containerization platform to package the application.
-Google Cloud: Cloud platform for hosting the application.

### API Endpoints
#### User Endpoints	
- "POST /users": Creates a new user.
	- Request body (json):
    {
      "name": "string",
      "userType": "string",
      "status": "string"
    }
	
	- Response (json):
	{
      "id": "string",
      "name": "string"
    }

- "DELETE /users/<id>": Deletes a user by ID.

- "GET /users": Retrieve all users.

- "POST /users/<id>/roles": Assign a role to a user.
	- Request body (json):
    {
      "user_id": "string",
      "role": "string"
    }

- "DELETE /users/<id>/roles/<role_id>": Remove a role from a user.
	- Request body (json):
    {
      "user_id": "string",
      "role": "string"
    }

#### Role Endpoints
- "POST /roles": Creates a new role.
	- Request body (json):
	{
	  "name": "string",
	  "description": "string",
	  "roleType": "string",
	  "scope": "string"
	}
	
	- Response (json):
	{
      "id": "string",
      "name": "string"
    }

- "PUT /roles/<id>": Modify an existing role by ID.
	- Request body (json):
	{
	  "name": "string",
	  "description": "string",
	  "roleType": "string",
	  "scope": "string"
	}
	
	- Response (json):
	{
      "id": "string",
      "name": "string"
    }

- "DELETE /roles/<id>": Deletes a role by ID.

- "GET /roles": Retrieve all roles.

### Deployment
