# Changelog

All notable changes to this project will be documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-11-12

### Fixed

- Crash (`KeyError: 'ack'`) on openziti routers v1.6.6 and later, which report link addresses under `link.ack`/`link.default` (or `single`) instead of `ack`/`payload`. The crash exited with 1 and caused keepalived to fail over a healthy router. Link addresses are now read regardless of key name.
- HA controllers: controller addresses are now collected from `ctrl.endpoint`, the `ctrl.endpoints` list and the router's controller endpoints file (`ctrl.endpointsFile`, default `endpoints.yml` next to the router config). Previously a `ctrl.endpoints` list made the script always return 0, and only one controller's co-located fabric router link was ignored.

### Changed

- An unexpected health check response format is now logged as an error and returns 1 instead of crashing.

## [1.1.0] - 2023-08-08

### Added

- Additional check - current circuit count

### Updated

- vrrp_notify.sh script - using ip command to get interface ip address instead of host command

## [1.0.0] - 2023-06-30

- Initial version
