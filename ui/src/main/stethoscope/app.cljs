(ns stethoscope.app
  (:require [re-frame.core :as rf]
            [stethoscope.events]
            [stethoscope.subs]
            [stethoscope.views :refer [render]]))

(defn ^:dev/after-load clear-cache-and-render! []
  (rf/clear-subscription-cache!)
  (render))

(defn main []
  (rf/dispatch-sync [:init])
  (rf/dispatch [:load-files])
  (render))
