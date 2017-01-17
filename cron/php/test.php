<?php 

$handle = @fopen("../etc/fb-product-broadcast.conf", 'r');
if ($handle) {
  while (($buffer = fgets($handle, 4096)) !== false) {
    if (preg_match('/^[#\s]+$/i', $buffer)) {
      echo("Comment or empty\n");
      continue;
    
    } else {
      preg_match('/^(?P<prop>[a-zA-Z_.+-]+)\s+(?P<val>[a-zA-Z_.+-]+)$/', $buffer, $match_arr);
      foreach ($match_arr as $key=>$val) {
        echo("match_arr['". $key ."']=". $val ."\n");
      }
    }
  }

  if (!feof($handle)) {
    break;
  }
  
  fclose($handle);

} else {
  echo("Couldn't open template!\n");
}

?>