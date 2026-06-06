import ReactNativeHapticFeedback from "react-native-haptic-feedback";

const options = {
  enableVibrateFallback: true,
  ignoreAndroidSystemSettings: false,
};

export enum NotificationFeedbackType {
  Success = "notificationSuccess",
  Warning = "notificationWarning",
  Error = "notificationError",
}

export enum ImpactFeedbackStyle {
  Light = "impactLight",
  Medium = "impactMedium",
  Heavy = "impactHeavy",
}

export const Haptics = {
  NotificationFeedbackType,
  ImpactFeedbackStyle,
  notificationAsync: async (type: NotificationFeedbackType) => {
    ReactNativeHapticFeedback.trigger(type, options);
  },
  selectionAsync: async () => {
    ReactNativeHapticFeedback.trigger("selection", options);
  },
  impactAsync: async (style: ImpactFeedbackStyle) => {
    ReactNativeHapticFeedback.trigger(style, options);
  },
};
