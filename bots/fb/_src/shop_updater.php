<?php


define('DB_HOST', "138.197.216.56");
define('DB_NAME', "prebot_marketplace");
define('DB_USER', "pre_usr");
define('DB_PASS', "f4zeHUga.age");


// make the connection
$db_conn = mysqli_connect(DB_HOST, DB_USER, DB_PASS) or die("Could not connect to database\n");

// select the proper db
mysqli_select_db($db_conn, DB_NAME) or die("Could not select database\n");
mysqli_set_charset($db_conn, 'utf8');



$query = 'SELECT `id`, `display_name`, `prebot_url` FROM `products` WHERE `storefront_id` IN (SELECT `id` FROM `storefronts` WHERE `display_name` LIKE "% e-Shop");';
$result = mysqli_query($db_conn, $query);

while($product_obj = mysqli_fetch_object($result)) {
  $display_name = str_replace(" Snaps", " Money Guide", $product_obj->display_name);
  $url_name = str_replace(" Snaps", "MoneyGuide", $product_obj->display_name);
  $url = str_replace("Snaps", "MoneyGuide", $product_obj->prebot_url);
  
  echo ("display_name:[". $display_name ."]\n");
  echo ("url_name:[". $url_name ."]\n");
  echo ("url:[". $url ."]\n");
  echo ("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=\n");
  
  $query = 'UPDATE `products` SET `name` = "'. $url_name .'", `display_name` = "'. $display_name .'", `prebot_url` = "'. $url .'" WHERE `id` = '. $product_obj->id .' LIMIT 1;';
  $r = mysqli_query($db_conn, $query);
}

mysqli_free_result($result);

// close db
if ($db_conn) {
	mysqli_close($db_conn);
	$db_conn = null;
}


?>
