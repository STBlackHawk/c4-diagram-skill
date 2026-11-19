# Bookshop

An online shop that sells printed books to the public. Shop staff keep the stock and the prices current.

## People

**Customer**:
A person who orders books from the shop.
_Avoid_: client, buyer, user

**Shop staff**:
A person who works for the shop and keeps the stock, the prices and the open orders current.
_Avoid_: admin, operator

## Selling

**Catalogue**:
The list of books that the shop can sell, with title, author, cover and price.
_Avoid_: product list

**Order**:
A request from a customer to buy one or more books at the prices shown when the customer pays.
_Avoid_: purchase, basket, cart

**Stock**:
The number of copies of each book that the shop holds now.
_Avoid_: inventory

**Invoice**:
The PDF that records an order, its prices and its payment.
_Avoid_: bill, receipt
