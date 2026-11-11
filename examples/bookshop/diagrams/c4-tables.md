## Inputs and outputs per user type

| User type | Group | Sends in | Gets out |
|---|---|---|---|
| Customer (person) | Public | searches, orders, payment details, reviews | search results, order confirmations, invoices (PDF), shipping updates |
| Shop staff (person) | Internal | stock counts, price changes, order status changes | low-stock alerts, daily sales report |

## External systems

| External system | Group | The system sends | The system receives |
|---|---|---|---|
| Payment provider | Money | creates charges on | posts payment events to |
| Email service | Messaging | sends email through |  |
| Book catalogue API | Data | looks up titles on | returns book metadata to |

## Containers

| Container | Kind | Technology | Does |
|---|---|---|---|
| Web app | app | Next.js 16 | Shop front and staff admin pages |
| API | app | Go 1.24, net/http | Orders, stock, payments. Serves the web app |
| Postgres | store | Postgres 16 | Orders, stock, customers |
| Worker | app | Go 1.24 | Sends email, builds invoices, nightly reports |
| Object storage | store | S3-compatible bucket | Invoice PDFs and cover images |

## Relationships

| From | To | Label | Technology |
|---|---|---|---|
| customer | web | orders on | HTTPS |
| staff | web | manages stock | HTTPS |
| web | api | sends requests | JSON over HTTPS |
| api | postgres | reads and writes | SQL |
| api | worker | enqueues jobs | Postgres queue |
| api | payments | creates charges | HTTPS |
| api | catalogue | looks up titles | HTTPS |
| worker | email | sends email | HTTPS |

## Glossary

- API: application programming interface
- HTTPS: HTTP over TLS
- SQL: structured query language
- PDF: portable document format
