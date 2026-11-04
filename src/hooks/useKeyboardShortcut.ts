import { useEffect, useCallback } from "react";

type KeyCombo = {
  key: string;
  ctrl?: boolean;
  shift?: boolean;
  alt?: boolean;
  meta?: boolean;
};

export function useKeyboardShortcut(
  combo: KeyCombo,
  callback: (e: KeyboardEvent) => void,
  enabled: boolean = true
) {
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (!enabled) return;

      const matchCtrl = combo.ctrl ? event.ctrlKey || event.metaKey : true;
      const matchShift = combo.shift ? event.shiftKey : !event.shiftKey;
      const matchAlt = combo.alt ? event.altKey : !event.altKey;
      const matchKey = event.key.toLowerCase() === combo.key.toLowerCase();

      if (matchCtrl && matchShift && matchAlt && matchKey) {
        event.preventDefault();
        callback(event);
      }
    },
    [combo, callback, enabled]
  );

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);
}
