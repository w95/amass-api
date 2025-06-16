# Amass API

Amass API is a Flask-based web application designed to interact with OWASP Amass, enabling domain enumeration via a simple REST API. For example, this API can be used by cybersecurity professionals to automate the discovery of subdomains during penetration testing, saving time and effort compared to manual methods. It provides options for recursive enumeration and brute-forcing subdomains, with results saved in a structured format.

## Features

- Perform domain enumeration using Amass, providing an automated and efficient way to discover subdomains without manual intervention.
- Support for recursive enumeration with a configurable minimum for recursion.
- Enable brute-forcing of subdomains.
- API endpoint to fetch results in JSON format.

## Prerequisites

- Docker
- Docker Compose

## Installation

### Using Docker Compose

You can use the prebuilt Docker image from Docker Hub to quickly deploy the API:
```bash
docker pull enrikenur/amass-api
```

Follow these steps to set up the application:

1. Clone the repository:
   ```bash
   git clone https://github.com/w95/amass-api
   cd amass-api
   ```
2. Build and start the application using Docker Compose:
   ```bash
   docker-compose up --build
   ```
3. Once running, access the API at `http://localhost:5000`.

## API Endpoints

### `/amass` (POST)

Trigger a domain enumeration.

#### Request Body (JSON)

| Parameter           | Type    | Required | Description                                                    |
| ------------------- | ------- | -------- | -------------------------------------------------------------- |
| `domain`            | String  | Yes      | The target domain for enumeration.                             |
| `brute`             | Boolean | No       | Enable brute-forcing of subdomains. Default: `false`.          |
| `min_for_recursive` | Integer | No       | Minimum number of findings to trigger recursion. Default: `2`. |

#### Example Request

```json
{
  "domain": "example.com",
  "brute": true,
  "min_for_recursive": 2
}
```

#### Response

- **Success**:
  ```json
  {
    "status": "success",
    "message": "Amass enumeration completed.",
    "output": [
      "subdomain1.example.com",
      "subdomain2.example.com"
    ]
  }
  ```
- **Error**:
  ```json
  {
    "status": "error",
    "message": "Domain is required"
  }
  ```

## License

This project is licensed under the MIT License. See `LICENSE` for more details.

## Acknowledgments

- [OWASP Amass](https://github.com/OWASP/Amass) for providing the enumeration tool.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your changes.