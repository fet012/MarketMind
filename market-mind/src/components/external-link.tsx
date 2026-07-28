/** @jsxImportSource react */
import { Href, Link } from "expo-router";
import {
  openBrowserAsync,
  WebBrowserPresentationStyle,
} from "expo-web-browser";
import type { ComponentProps, MouseEvent } from "react";
import type { GestureResponderEvent } from "react-native";

type Props = Omit<ComponentProps<typeof Link>, "href"> & {
  href: Href & string;
};

export function ExternalLink({ href, ...rest }: Props) {
  return (
    <Link
      target="_blank"
      {...rest}
      href={href}
      onPress={async (
        event: GestureResponderEvent | MouseEvent<HTMLAnchorElement>,
      ) => {
        const processEnv = (globalThis as any).process?.env as
          | { EXPO_OS?: string }
          | undefined;
        if (processEnv?.EXPO_OS !== "web") {
          // Prevent the default behavior of linking to the default browser on native.
          event.preventDefault?.();
          // Open the link in an in-app browser.
          await openBrowserAsync(href, {
            presentationStyle: WebBrowserPresentationStyle.AUTOMATIC,
          });
        }
      }}
    />
  );
}
