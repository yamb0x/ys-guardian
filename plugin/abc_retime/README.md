# Alembic Retime

* Description: Percentage based alembic & mograph cache retimer for Cinema 4D.
* Copyright: AXISFX LTD
* Author: Ewan Davidson
* Email: ewan@axisfx.design
* Release Date: 31.01.2022
* Current Version: 1.1.3

## Supported Objects/Tags

* Alembic Object
* Alembic Tag
* Point Cache Tag (Changing the offset doesn't seem to be working)
* Mograph Cache Tag (Changing the offset doesn't seem to be working)
* X-Particles Cache

## Installation

* Click the green 'Code' button
* Click 'Download ZIP'
* Extract to the 'Cinema 4D RXX/Plugins folder'
* Restart Cinema 4D

## Changelog

### 1.1.3  |  23.02.2023

* Added support for Alembic Tag

### 1.1.2  |  23.02.2023

* Fixed quantizing in frame mode
* Offset applies before start frame (speed mode)

### 1.1.1  |  22.02.2023

* 'Retime using frame number' is enabled by default
* Playback offset doesn't apply to retime using frame number
* Frame number key frames are visible in the f-curve
* Remove keyframe track on the parameter that is being set

### 1.1.0  |  02.04.2022

* Added support for importing [retime data](https://github.com/axisfx2/cross-platform-retime)

### 1.0.2  |  22.02.2022

* Updated icon

### 1.0.1  |  01.02.2022

* Fixes for point & mograph cache tags
* Added support for XP Cache
* Added optional frame parameter - control retimes with the frame number instead of speed
* Updated labels

### 1.0.0  |  31.01.2022

* Initial release