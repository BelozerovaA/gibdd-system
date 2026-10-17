module.exports = {
  preset: '@react-native/jest-preset',
  // эти пакеты поставляются как ES-модули, их нужно преобразовывать
  transformIgnorePatterns: [
    'node_modules/(?!((jest-)?react-native|@react-native(-community)?|@react-native-async-storage|@react-native-picker|@react-navigation)/)',
  ],
  moduleNameMapper: {
    // штатный мок хранилища из пакета (в тестах настоящего хранилища нет)
    '^@react-native-async-storage/async-storage$': '@react-native-async-storage/async-storage/jest',
  },
  setupFiles: ['<rootDir>/jest.setup.js'],
};
