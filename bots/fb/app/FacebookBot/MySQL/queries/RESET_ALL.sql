

#-- WIPES ALL ROWS + RESETS AUTO-INC TO 1
#- -#- -#- -#- -#- -#- -#- -#- -#- -#- -#- -#- -#- -#- -#- -#- -#- -#- -#- -#- -#- -#- -#
DELETE FROM `users` ; ALTER TABLE `users` AUTO_INCREMENT = 1;
DELETE FROM `chat_logs` ; ALTER TABLE `chat_logs` AUTO_INCREMENT = 1;
DELETE FROM `storefronts` ; ALTER TABLE `storefronts` AUTO_INCREMENT = 1;
DELETE FROM `products` ; ALTER TABLE `products` AUTO_INCREMENT = 1;
DELETE FROM `subscriptions` ; ALTER TABLE `subscriptions` AUTO_INCREMENT = 1
#- -#- -#- -#- -#- -#- -#- -#- -#- -#- -#- -#- -#- -#- -#- -#- -#- -#- -#- -#- -#- -#- -#