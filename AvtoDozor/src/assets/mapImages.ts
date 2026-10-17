import type { ImageSourcePropType } from 'react-native';

/** Соотношение сторон карт (все картинки одного размера: 2400x1438). */
export const MAP_ASPECT = 2400 / 1438;

// Metro требует статические пути в require(), поэтому динамически собрать имя файла нельзя.
const CAMERA_MAPS: Record<number, ImageSourcePropType> = {
  1: require('./maps/cam_1.jpg'),
  2: require('./maps/cam_2.jpg'),
  3: require('./maps/cam_3.jpg'),
  4: require('./maps/cam_4.jpg'),
  5: require('./maps/cam_5.jpg'),
  6: require('./maps/cam_6.jpg'),
  7: require('./maps/cam_7.jpg'),
  8: require('./maps/cam_8.jpg'),
  9: require('./maps/cam_9.jpg'),
  10: require('./maps/cam_10.jpg'),
  11: require('./maps/cam_11.jpg'),
  12: require('./maps/cam_12.jpg'),
  13: require('./maps/cam_13.jpg'),
  14: require('./maps/cam_14.jpg'),
  15: require('./maps/cam_15.jpg'),
};

const ALL_MAP: ImageSourcePropType = require('./maps/all_map.jpg');

/** Карта с камерой №N, выделенной красным; для неизвестного номера возвращается общая карта. */
export function getMapImage(cameraNumber: number | null | undefined): ImageSourcePropType {
  if (cameraNumber != null && CAMERA_MAPS[cameraNumber]) {
    return CAMERA_MAPS[cameraNumber];
  }
  return ALL_MAP;
}
