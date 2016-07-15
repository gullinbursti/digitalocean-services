/*
 Navicat Premium Data Transfer

 Source Server         : kik-bot
 Source Server Type    : SQLite
 Source Server Version : 3008000
 Source Database       : main

 Target Server Type    : SQLite
 Target Server Version : 3008000
 File Encoding         : utf-8

 Date: 07/14/2016 22:05:36 PM
*/

PRAGMA foreign_keys = false;

-- ----------------------------
--  Table structure for faq_content
-- ----------------------------
DROP TABLE IF EXISTS "faq_content";
CREATE TABLE "faq_content" (
	 "id" INTEGER PRIMARY KEY AUTOINCREMENT,
	 "faq_id" INTEGER(255,0) NOT NULL DEFAULT 0,
	 "content" TEXT NOT NULL,
	UNIQUE ("id" ASC)
);
INSERT INTO "main".sqlite_sequence (name, seq) VALUES ("faq_content", '4');

-- ----------------------------
--  Records of faq_content
-- ----------------------------
BEGIN;
INSERT INTO "faq_content" VALUES 
(NULL, 1, 'Pokémon Go (stylized as Pokémon GO) is a free-to-play location-based augmented reality mobile game developed by Niantic and published by The Pokémon Company as part of the Pokémon franchise. It was released worldwide in July 2016 for iOS and Android devices.'),
(NULL, 1, 'The game allows players to capture, battle, and train virtual Pokémon who appear throughout the real world. It makes use of GPS and the camera of compatible devices. Although the game is free-to-play, it supports in-app purchases of additional gameplay items. An optional companion Bluetooth wearable device, the Pokémon Go Plus, is planned for future release and will alert users when Pokémon are nearby.'),
(NULL, 1, 'The game received mixed critical reception. It was praised by some medical professionals for potentially improving the mental and physical health of players, but attracted some controversy due to reports of causing accidents and being a public nuisance to some locations. It was one of the most downloaded smartphone apps upon its release, and was a boon to the stock value of Nintendo, which owns a part of The Pokémon Company. Within a week of release, it became the most active mobile game ever in the United States with more than 21 million players surpassing the previous record held by Candy Crush Saga.');

INSERT INTO "faq_content" VALUES 
(NULL, 2, 'Dota 2 is a free-to-play multiplayer online battle arena (MOBA) video game developed and published by Valve Corporation.'),
(NULL, 2, 'The game is the stand-alone sequel to Defense of the Ancients (DotA), a mod for the 2002 video game Warcraft III: Reign of Chaos and its expansion pack, The Frozen Throne.'),
(NULL, 2, 'Dota 2 was released for Microsoft Windows, OS X, and Linux in July 2013, following a Windows-only public beta testing phase that began in 2011, and is one of the most actively played games on Steam, with maximum peaks of over a million concurrent players.');

INSERT INTO "faq_content" VALUES 
(NULL, 3, 'League of Legends is a multiplayer online battle arena video game developed and published by Riot Games forMicrosoft Windows and OS X.'),
(NULL, 3, 'The game follows a freemium model and is supported by microtransactions, and was inspired by the Warcraft III: The Frozen Throne mod, Defense of the Ancients.');

INSERT INTO "faq_content" VALUES 
(NULL, 4, 'Counter-Strike (officially abbreviated as CS) is a series of multiplayer first-person shooter video games, in which teams of terrorists and counter-terrorists battle to, respectively, perpetrate an act of terror (bombing, hostage-taking) and prevent it (bomb defusal, hostage rescue'),
(NULL, 4, 'The series began on Windows in 1999 with the first version of Counter-Strike.'),
(NULL, 4, 'It was initially released as a modification for Half-Life and designed by Minh "Gooseman" Le and Jess "Cliffe" Cliffe, before the rights to the game''s intellectual property were acquired by Valve Corporation, the developers of Half-Life.');
COMMIT;

PRAGMA foreign_keys = true;
