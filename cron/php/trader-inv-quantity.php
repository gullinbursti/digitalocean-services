<?php

define('DB_HOST', "external-db.s4086.gridserver.com");
define('DB_NAME', "db4086_modd");
define('DB_USER', "db4086_modd_usr");
define('DB_PASS', "f4zeHUga.age");

// lower 
define('MINIUM_QUANTITY', 20);

// make the connection
$db_conn = mysqli_connect(DB_HOST, DB_USER, DB_PASS) or die("Could not connect to database\n");

// select the proper db
mysqli_select_db($db_conn, DB_NAME) or die("Could not select database\n");
mysqli_set_charset($db_conn, 'utf8');


function desc_sort($a, $b) {
  if ($a == $b) {
    return (0);
  }
  
  return (($a < $b) ? -1 : 1);
}


$inv_arr = array();
$quantity_bit = 0x00;

// fetch total available steam inventory
$query = 'SELECT SUM(`quantity`) AS `tot` FROM `flip_inventory` WHERE `type` = 1 AND `enabled` = 1;';
$result = mysqli_query($db_conn, $query);

$tot = mysqli_fetch_object($result)->tot;
$quantity_bit |= ($tot <= MINIUM_QUANTITY) ? 0x01 : 0x00;
$quantity_bit |= ($tot == 0) ? 0x10 : 0x00;
$payload_obj = array();

echo ("Steam inventory left: ". $tot ."\n");

// tot drops below threshhold
if (($quantity_bit & 0x01) == 0x01) {
  $query = 'SELECT `name`, `quantity` FROM `flip_inventory` WHERE `quantity` > 0 AND `type` = 1 AND `enabled` = 1 ORDER BY `quantity` DESC;';
  $result = mysqli_query($db_conn, $query);
  
  // tally up items
  while ($inv_obj = mysqli_fetch_object($result)) {
    if (!array_key_exists($inv_obj->name, $inv_arr)) {
      $inv_arr[$inv_obj->name] = 0;
    }
      
    $inv_arr[$inv_obj->name] += $inv_obj->quantity;
  }
  
  uasort($inv_arr, 'desc_sort');
  
  // report as text
  $txt_body = "";
  foreach (array_reverse($inv_arr) as $key=>$val) {
    $txt_body .= sprintf("*%-2s*\t_%s_\n", $val, $key);
  }
  
  $payload_obj = array(
    'channel'  => "#pre",
    'username' => "steam-trader",
    'icon_url' => "http://icon-icons.com/icons2/413/PNG/256/steam_41101.png",
    'text'     => "Running low on flip coin items, only *". $tot ."* remain!\n". $txt_body
  );

} elseif (($quantity_bit & 0x11) == 0x11) {
  $payload_obj = array(
    'channel'  => "#pre",
    'username' => "steam-trader",
    'icon_url' => "http://icon-icons.com/icons2/413/PNG/256/steam_41101.png",
    'text'     => "*No items* left to trade for flip coin!"
  );
}


if (count($payload_obj) > 0) {
  $ch = curl_init();
	curl_setopt($ch, CURLOPT_URL, "https://hooks.slack.com/services/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");
	curl_setopt($ch, CURLOPT_POST, 1);
	curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($payload_obj));
	curl_setopt($ch, CURLOPT_HTTPHEADER, array("Content-Type: application/json"));
	curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1);
	curl_setopt($ch, CURLOPT_FAILONERROR, 1);
	curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 300);
	curl_setopt($ch, CURLOPT_TIMEOUT, 60);

	$response = curl_exec($ch);
	curl_close($ch);
	
	if (strlen($response) > 0) {
	  echo($response ."\n");
	}
}


// close db
if ($db_conn) {
	mysqli_close($db_conn);
	$db_conn = null;
}

?>