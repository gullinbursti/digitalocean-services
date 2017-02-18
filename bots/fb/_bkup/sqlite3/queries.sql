

-- select * from products where storefront_id in (select id from storefronts where owner_id like "90%0" and length(owner_id) = 16)
-- delete from products where storefront_id in (select id from storefronts where owner_id like "9%" and length(owner_id) = 16)
-- update products set type_id

-- select * from storefronts where owner_id like "90%0" and length(owner_id) = 16
-- delete from storefronts where owner_id like "9%" and length(owner_id) = 16

-- select * from customers where fb_psid like "90%0" and length(fb_psid) = 16
-- delete from customers where fb_psid like "9%" and length(fb_psid) = 16

-- update purchases set type = 1


-- select * from purchases where claim_state = 1 and (storefront_id in (select id from storefronts where owner_id == "1448213991869039") or customer_id in (select id from customer where fb_psid == "1448213991869039"))

-- select * from storefronts where owner_id like "90%0"





delete from storefronts where id != 524288
