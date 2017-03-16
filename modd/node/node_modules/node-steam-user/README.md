# SteamUser

This is a handler for user account-related functionality, to be used with the `node-steam` module. It is basically a straight copy of Seishun's module [here](https://github.com/seishun/node-steam/tree/master/lib/handlers/user).

Initialize it by passing a SteamClient instance to the constructor.

```js
var Steam     = require('node-steam'),
    SteamUser = require('node-steam-user');

var client = new Steam.SteamClient();

Steam.SteamUser = new SteamUser(client);
```

## Methods

### logOn(logOnDetails)

Sends a ClientLogon message. `logOnDetails` is a [`CMsgClientLogon`](https://github.com/SteamRE/SteamKit/blob/master/Resources/Protobufs/steamclient/steammessages_clientserver.proto) object. It's used as-is except `protocol_version` is set to the currently implemented protocol version.

### gamesPlayed(gamesPlayed)

Tells Steam you are playing game(s). `gamesPlayed` is a [`CMsgClientGamesPlayed`](https://github.com/SteamRE/SteamKit/blob/master/Resources/Protobufs/steamclient/steammessages_clientserver.proto) object.

## Events

### 'loggedOn'

Emitted when a  [`CMsgClientLogonResponse`](https://github.com/SteamRE/SteamKit/blob/master/Resources/Protobufs/steamclient/steammessages_clientserver.proto#L94) message is received with an `eresult` indicating successful logon. Returns a decoded  `CMsgClientLogonResponse` object.

### 'logOnError'

Emitted when a  [`CMsgClientLogonResponse`](https://github.com/SteamRE/SteamKit/blob/master/Resources/Protobufs/steamclient/steammessages_clientserver.proto#L94) message is received with an `eresult` indicating unsuccessful logon. Returns a decoded  `CMsgClientLogonResponse` object. To know what happened, have a look at the standard [Steam eresults](https://github.com/SteamRE/SteamKit/blob/master/Resources/SteamLanguage/eresult.steamd) and handle accordingly.

### 'updateMachineAuth'

Emitted when a [`CMsgClientUpdateMachineAuth`](https://github.com/SteamRE/SteamKit/blob/master/Resources/Protobufs/steamclient/steammessages_clientserver_2.proto) message is received, usually in response to an invalid (or no) sentry file. Returns the decoded `CMsgClientUpdateMachineAuth` object and a `callback`.

Call `callback` with a [`CMsgClientUpdateMachineAuthResponse`](https://github.com/SteamRE/SteamKit/blob/master/Resources/Protobufs/steamclient/steammessages_clientserver_2.proto) object to accept this sentry update.
