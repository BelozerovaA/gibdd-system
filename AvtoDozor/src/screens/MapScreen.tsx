import React, { useState } from 'react';
import { Image, LayoutChangeEvent, ScrollView, StyleSheet, Text, View } from 'react-native';
import { getMapImage, MAP_ASPECT } from '../assets/mapImages';
import AppButton from '../components/AppButton';
import Screen from '../components/Screen';
import { useAlerts } from '../context/AlertContext';
import { colors } from '../theme';

const MIN_ZOOM = 0.5;
const MAX_ZOOM = 4;
const ZOOM_STEP = 0.5;

/**
 * Карта (ТЗ, рисунок 6): камеры видеофиксации, масштабирование.
 * При срабатывании тревоги показывается карта с выделенной камерой.
 */
export default function MapScreen() {
  const { highlight, clearHighlight } = useAlerts();
  const [zoom, setZoom] = useState(1);
  const [box, setBox] = useState({ width: 0, height: 0 });

  const onLayout = (e: LayoutChangeEvent) => {
    const { width, height } = e.nativeEvent.layout;
    setBox({ width, height });
  };

  // при масштабе 100% карта занимает всю высоту окна, дальше её можно увеличивать и прокручивать
  const baseWidth = Math.max(box.height * MAP_ASPECT, box.width);
  const imageWidth = baseWidth * zoom;
  const imageHeight = imageWidth / MAP_ASPECT;

  return (
    <Screen title="Карта">
      <View style={styles.toolbar}>
        <View style={styles.zoomButton}>
          <AppButton
            title="Увеличить +"
            small
            disabled={zoom >= MAX_ZOOM}
            onPress={() => setZoom(z => Math.min(MAX_ZOOM, z + ZOOM_STEP))}
          />
        </View>
        <View style={styles.zoomButton}>
          <AppButton
            title="Уменьшить −"
            small
            disabled={zoom <= MIN_ZOOM}
            onPress={() => setZoom(z => Math.max(MIN_ZOOM, z - ZOOM_STEP))}
          />
        </View>
        <Text style={styles.zoomLabel} testID="zoom-label">
          {Math.round(zoom * 100)}%
        </Text>
      </View>

      {highlight ? (
        <View style={styles.banner} testID="highlight-banner">
          <Text style={styles.bannerText}>
            <Text style={styles.bannerBold}>{highlight.plate}</Text> зафиксирован на камере №
            {highlight.camera}: {highlight.address}
          </Text>
          <AppButton title="Общая карта" small onPress={clearHighlight} />
        </View>
      ) : null}

      <View testID="map-box" style={styles.mapBox} onLayout={onLayout}>
        {box.width > 0 ? (
          <ScrollView horizontal nestedScrollEnabled bounces={false}>
            <ScrollView nestedScrollEnabled bounces={false}>
              <Image
                testID="map-image"
                source={getMapImage(highlight?.camera)}
                style={{ width: imageWidth, height: imageHeight }}
                resizeMode="stretch"
              />
            </ScrollView>
          </ScrollView>
        ) : null}
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  toolbar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginBottom: 10,
  },
  zoomButton: {
    flex: 1,
  },
  zoomLabel: {
    minWidth: 48,
    textAlign: 'right',
    fontSize: 14,
    color: colors.muted,
  },
  banner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    borderWidth: 1,
    borderColor: colors.danger,
    borderRadius: 8,
    padding: 8,
    marginBottom: 10,
  },
  bannerText: {
    flex: 1,
    fontSize: 13,
    color: colors.text,
  },
  bannerBold: {
    fontWeight: '700',
    color: colors.danger,
  },
  mapBox: {
    flex: 1,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    borderRadius: 8,
    overflow: 'hidden',
    backgroundColor: '#F3F4F6',
  },
});
