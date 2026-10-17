import { createNavigationContainerRef, NavigatorScreenParams } from '@react-navigation/native';

export type TabParamList = {
  Profile: undefined;
  MyWanted: undefined;
  AllWanted: undefined;
  Map: undefined;
  History: undefined;
};

export type RootStackParamList = {
  Login: undefined;
  Main: NavigatorScreenParams<TabParamList> | undefined;
};

/** Позволяет переключать вкладки не из экрана (например, открыть карту при оповещении). */
export const navigationRef = createNavigationContainerRef<RootStackParamList>();
