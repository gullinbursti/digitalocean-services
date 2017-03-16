'use strict';
/* jshint node:true, esversion:6, latedef:nofunc */

var _            = require('lodash'),
    EventEmitter = require('events').EventEmitter,
    Steam        = require('node-steam'),
    SteamID      = require('steamid');

var EMsg   = Steam.EMsg,
    Schema = Steam.Internal;

function SteamUser(client) {
  this._client = client;
  this._client.on('message', function(header, body, callback) {
    if (header.msg in handlers)
      handlers[header.msg].call(this, body, callback);
  }.bind(this));
}

require('util').inherits(SteamUser, EventEmitter);

// Methods

SteamUser.prototype.logOn = function(logOnDetails) {

  if (this._client.loggedOn) {
    this.emit('error', new Error('EALREADYLOGGEDON'));
    return;
  }

  // construct temporary SteamID to use with ClientLogon request
  var tmpId = new SteamID();

  tmpId.universe = SteamID.Universe.PUBLIC;
  tmpId.type = SteamID.Type.INDIVIDUAL;
  tmpId.instance = SteamID.Instance.DESKTOP;
  tmpId.accountid = 0;

  this._client.steamID = tmpId.getSteamID64();

  logOnDetails.protocol_version = 65575;

  this._client.send({
    msg: EMsg.ClientLogon,
    proto: {}
  }, new Schema.CMsgClientLogon(logOnDetails).toBuffer());

};

SteamUser.prototype.gamesPlayed = function(gamesPlayed) {
  this._client.send({
    msg: EMsg.ClientGamesPlayed,
    proto: {}
  }, new Schema.CMsgClientGamesPlayed(gamesPlayed).toBuffer());
};

// Handlers

var handlers = {};

handlers[EMsg.ClientLogOnResponse] = function(data) {

	var logonResp = Schema.CMsgClientLogonResponse.decode(data),
      eresult = logonResp.eresult;

	if (eresult == Steam.EResult.OK) {
    this._client.loggedOn = true;
    this._client.steamID = logonResp.client_supplied_steamid.toString();

		var hbDelay = logonResp.out_of_game_heartbeat_seconds;

		this._heartBeatFunc = setInterval(function() {
			this._client.send({
				"msg": EMsg.ClientHeartBeat,
				"proto": {}
			}, new Schema.CMsgClientHeartBeat().toBuffer());
		}.bind(this), hbDelay * 1000);

    this.emit('loggedOn', Steam._processProto(logonResp));
    return;

	} else {

    this.emit('logOnError', Steam._processProto(logonResp));

  }

};

handlers[EMsg.ClientLoggedOff] = function(data) {
	this._client.loggedOn = false;
	clearInterval(this._heartBeatFunc);

	var eresult = Schema.CMsgClientLoggedOff.decode(data).eresult;

	this.emit('loggedOff', eresult);
};

handlers[EMsg.ClientUpdateMachineAuth] = function(data, callback) {
  var machineAuth = Schema.CMsgClientUpdateMachineAuth.decode(data);

  this.emit('updateMachineAuth', Steam._processProto(machineAuth), function(response) {
    callback({
      msg: EMsg.ClientUpdateMachineAuthResponse,
      proto: {}
    }, new Schema.CMsgClientUpdateMachineAuthResponse(response).toBuffer());
  });
};

module.exports = SteamUser;
