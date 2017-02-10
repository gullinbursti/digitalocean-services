BEGIN TRANSACTION;
CREATE TABLE subscription (
	id INTEGER NOT NULL, 
	storefront_id INTEGER, 
	product_id INTEGER, 
	customer_id INTEGER, 
	enabled INTEGER, 
	added INTEGER, 
	PRIMARY KEY (id)
);
CREATE TABLE "storefront" (
  id              integer NOT NULL PRIMARY KEY,
  owner_id        text,
  creation_state  integer,
  type            integer,
  name            text,
  display_name    text,
  description     text,
  logo_url        text,
  video_url       text,
  prebot_url      text,
  giveaway        integer,
  bitcoin_addr    text,
  paypal_addr     text,
  views           integer,
  added           integer
);
CREATE TABLE "rating" (
  id          integer NOT NULL PRIMARY KEY,
  product_id  integer,
  fb_psid     text,
  stars       integer,
  added       integer
);
CREATE TABLE "purchas"
(
	"id" integer PRIMARY KEY NOT NULL,
	"customer_id" integer,
	"storefront_id" integer,
	"product_id" integer,
	"charge_id" text,
	"claim_state" integer,
	"added" integer
);
CREATE TABLE "product" (
  id                 integer NOT NULL PRIMARY KEY,
  storefront_id      integer,
  creation_state     integer,
  name               varchar(80),
  display_name       varchar(80),
  description        varchar(200),
  image_url          varchar(500),
  video_url          varchar(500),
  broadcast_message  varchar(200),
  attachment_id      varchar(100),
  price              float(50,2),
  prebot_url         varchar(128),
  release_date       integer,
  views              integer,
  avg_rating         float(50),
  added              integer
);
CREATE TABLE "payment"
(
    "id" integer PRIMARY KEY NOT NULL,
    "fb_psid" text,
    "full_name" text,
    "acct_number" text,
    "expiration" date,
    "cvc" text,
    "creation_state" integer,
    "added" integer
);
CREATE TABLE "direct_message"
(
	" id" integer NOT NULL,
	"purchase_id" integer DEFAULT 0 NOT NULL,
	"sender_id" integer DEFAULT 0 NOT NULL,
	"message_text" text,
	"message_json" text,
	"added" integer DEFAULT 0 NOT NULL
);
CREATE TABLE "customer" (
  id             integer NOT NULL PRIMARY KEY,
  fb_psid        text,
  fb_name        text,
  email          text,
  bitcoin_addr   text,
  referrer       text,
  stripe_id      text,
  card_id        text,
  storefront_id  integer,
  product_id     integer,
  purchase_id    integer,
  added          integer
, mode tiny DEFAULT 0 NOT NULL);
COMMIT;
