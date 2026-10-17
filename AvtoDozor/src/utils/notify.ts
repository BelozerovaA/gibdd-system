import { Alert, Platform, ToastAndroid } from 'react-native';

/** Короткое сообщение пользователю: тост на Android, окно на iOS. */
export function notify(message: string, long = false): void {
  if (Platform.OS === 'android') {
    ToastAndroid.show(message, long ? ToastAndroid.LONG : ToastAndroid.SHORT);
  } else {
    Alert.alert(message);
  }
}
