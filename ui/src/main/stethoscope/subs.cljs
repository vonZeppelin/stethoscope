(ns stethoscope.subs
  (:require [re-frame.core :as rf]))

(rf/reg-sub
 :files
 (fn [db _]
   (:files db)))

(rf/reg-sub
 :loading-files?
 (fn [db _]
   (:loading-files? db)))
