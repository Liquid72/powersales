CREATE TABLE users
(
    id           int primary key identity,
    email        varchar(255) not null,
    first_name   varchar(255) not null,
    last_name    varchar(255) not null,
    country      varchar(255) not null,
    company_name varchar(255),
    industry     varchar(255)
);


CREATE TABLE categories
(
    id   int primary key identity,
    name varchar(255) not null
);



CREATE TABLE products
(
    id          int primary key identity,
    SKU         varchar(255) not null unique,
    name        varchar(255) not null,
    description varchar(255),
    price       int          not null,
    category_id int          not null,
    foreign key (category_id) references categories (id)
);


CREATE TABLE cart
(
    id       int primary key identity,
    user_id  int          not null,
    SKU      varchar(255) not null,
    quantity int          not null,
    foreign key (user_id) references users (id),
    foreign key (SKU) references products (SKU)
);


CREATE TABLE quotations
(
    id       int primary key identity,
    user_id  int          not null,
    SKU      varchar(255) not null,
    quantity int          not null,
    price    int          not null,
    foreign key (user_id) references users (id),
    foreign key (SKU) references products (SKU)
);

CREATE TABLE Orders
(
    order_id       int primary key identity,
    transaction_id varchar(255) not null,
    user_id        int          not null,
    order_date     date         not null,
    total_price    int          not null,
    status         varchar(255) not null,
    shipping_address varchar(255) not null,
    foreign key (user_id) references users (id)
);

CREATE TABLE OrderDetails
(
    order_id int          not null,
    SKU      varchar(255) not null,
    quantity int          not null,
    price    int          not null,
    foreign key (order_id) references Orders (order_id),
    foreign key (SKU) references products (SKU)
);