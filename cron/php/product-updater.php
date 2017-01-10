<?php 

define('DB_HOST', "external-db.s4086.gridserver.com");
define('DB_NAME', "db4086_modd");
define('DB_USER', "db4086_modd_usr");
define('DB_PASS', "f4zeHUga.age");


// make the connection
$db_conn = mysqli_connect(DB_HOST, DB_USER, DB_PASS) or die("Could not connect to database\n");

// select the proper db
mysqli_select_db($db_conn, DB_NAME) or die("Could not select database\n");
mysqli_set_charset($db_conn, 'utf8');

// reset all to disabled
$query = 'UPDATE `fb_products` SET `enabled` = 0;';
$result = mysqli_query($db_conn, $query);

// select closest to date - 24h
$query = 'SELECT `id`, `name` FROM `fb_products` WHERE `added` > DATE_SUB(NOW(), INTERVAL 24 HOUR) LIMIT 1;';
$result = mysqli_query($db_conn, $query);
$product_obj = mysqli_fetch_object($result);
mysqli_free_result($result);

echo("Today's product: [". $product_obj->id ."] \"". $product_obj->name ."\"\n");

// make it enabled
$query = 'UPDATE `fb_products` SET `enabled` = 1 WHERE `id` = '. $product_obj->id .';';
$result = mysqli_query($db_conn, $query);

// close db
if ($db_conn) {
	mysqli_close($db_conn);
	$db_conn = null;
}
?>
