PRAGMA foreign_keys = ON;

CREATE TABLE member (
    member_id TEXT NOT NULL,
    member_name TEXT NOT NULL,
    CONSTRAINT pk_member PRIMARY KEY (member_id),
    CONSTRAINT ck_member_id_length
        CHECK (length(member_id) BETWEEN 1 AND 20),
    CONSTRAINT ck_member_name_length
        CHECK (length(member_name) BETWEEN 1 AND 100)
);

CREATE TABLE category (
    category_code TEXT NOT NULL,
    category_name TEXT NOT NULL,
    CONSTRAINT pk_category PRIMARY KEY (category_code),
    CONSTRAINT ck_category_code_length
        CHECK (length(category_code) BETWEEN 1 AND 20),
    CONSTRAINT ck_category_name_length
        CHECK (length(category_name) BETWEEN 1 AND 100)
);

CREATE TABLE book (
    book_id TEXT NOT NULL,
    book_name TEXT NOT NULL,
    category_code TEXT NOT NULL,
    CONSTRAINT pk_book PRIMARY KEY (book_id),
    CONSTRAINT fk_book_category
        FOREIGN KEY (category_code)
        REFERENCES category (category_code)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,
    CONSTRAINT ck_book_id_length
        CHECK (length(book_id) BETWEEN 1 AND 20),
    CONSTRAINT ck_book_name_length
        CHECK (length(book_name) BETWEEN 1 AND 200)
);

CREATE TABLE book_order (
    order_id TEXT NOT NULL,
    member_id TEXT NOT NULL,
    order_datetime TEXT NOT NULL,
    order_status_code TEXT NOT NULL,
    CONSTRAINT pk_book_order PRIMARY KEY (order_id),
    CONSTRAINT fk_book_order_member
        FOREIGN KEY (member_id)
        REFERENCES member (member_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,
    CONSTRAINT ck_order_id_length
        CHECK (length(order_id) BETWEEN 1 AND 20),
    CONSTRAINT ck_order_datetime
        CHECK (datetime(order_datetime) IS NOT NULL),
    CONSTRAINT ck_order_status_code
        CHECK (order_status_code IN ('PAID', 'SHIPPING', 'DONE', 'CANCELLED'))
);

CREATE TABLE order_item (
    order_id TEXT NOT NULL,
    book_id TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(12, 2) NOT NULL,
    CONSTRAINT pk_order_item PRIMARY KEY (order_id, book_id),
    CONSTRAINT fk_order_item_order
        FOREIGN KEY (order_id)
        REFERENCES book_order (order_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,
    CONSTRAINT fk_order_item_book
        FOREIGN KEY (book_id)
        REFERENCES book (book_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,
    CONSTRAINT ck_order_item_quantity
        CHECK (quantity BETWEEN 1 AND 999),
    CONSTRAINT ck_order_item_unit_price_range
        CHECK (unit_price BETWEEN 0 AND 9999999999.99),
    CONSTRAINT ck_order_item_unit_price_scale
        CHECK (unit_price = round(unit_price, 2))
);