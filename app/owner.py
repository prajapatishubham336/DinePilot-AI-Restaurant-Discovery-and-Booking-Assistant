import pandas as pd
import streamlit as st

from .availability import (create_restaurant, create_slot, list_restaurants, list_slots,)
from .db import (list_all_bookings, update_booking_status,)


# OWNER DASHBOARD
def owner_dashboard():
    tabs = st.tabs(
        [
            "🏪 Restaurant Setup",
            "🕒 Time Slots",
            "📊 Availability",
            "📋 Bookings",
        ]
    )

    # RESTAURANT SETUP
    with tabs[0]:
        st.markdown("### 🏪 Restaurant Configuration")
        with st.form("restaurant_setup"):
            restaurant_name = st.text_input("Restaurant Name", placeholder="DinePilot Restaurant",)
            col1, col2 = st.columns(2)
            total_tables = col1.number_input(
                "Total Tables",
                min_value=1,
                max_value=500,
                value=20,
                step=1,
            )

            table_capacity = col2.number_input(
                "Seats per Table",
                min_value=1,
                max_value=20,
                value=4,
                step=1,
            )

            submitted = st.form_submit_button(
                "💾 Save Restaurant",
                type="primary",
                use_container_width=True,
            )

        if submitted:
            if not restaurant_name.strip():
                st.error("Enter restaurant name.")

            else:

                create_restaurant(
                    restaurant=restaurant_name.strip(),
                    total_tables=int(total_tables),
                    table_capacity=int(table_capacity),
                )

                st.success("✅ Restaurant configuration saved.")
        st.markdown("### Existing Restaurants")
        restaurants = list_restaurants()
        if restaurants:
            df = pd.DataFrame(restaurants, columns=["Restaurant","Total Tables","Seats / Table",],)
            st.dataframe(df, use_container_width=True, hide_index=True,)

        else:
            st.info("No restaurant configured yet.")

    # TIME SLOTS
    with tabs[1]:
        st.markdown("### 🕒 Create Restaurant Time Slots")
        restaurants = list_restaurants()
        if not restaurants:
            st.warning("Create a restaurant first.")
        else:
            restaurant_names = [row[0]  for row in restaurants]
            selected_restaurant = st.selectbox(
                "Restaurant",
                restaurant_names,
                key="owner_slot_restaurant",
            )

            slot_date = st.date_input("Date", key="owner_slot_date",)

            slot_times = st.text_input(
                "Time Slots",
                placeholder=(
                    "18:00, 18:30, 19:00, "
                    "19:30, 20:00, 20:30"
                ),
                key="owner_slot_times",
            )

            if st.button("➕ Create Slots", type="primary", use_container_width=True,):
                if not slot_times.strip():
                    st.error("Enter at least one time slot.")
                else:
                    times = [x.strip() for x in slot_times.split(",") if x.strip()]
                    created = 0
                    invalid = []
                    for slot_time in times:
                        try:
                            hour, minute = map(int, slot_time.split(":"),)
                            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                                invalid.append(slot_time)
                                continue

                            formatted_time = (f"{hour:02d}:{minute:02d}")
                            ok, message = create_slot(
                                restaurant=selected_restaurant,
                                booking_date=str(slot_date),
                                booking_time=formatted_time,
                            )

                            if ok:
                                created += 1
                        except ValueError:
                            invalid.append(slot_time)

                    if created:
                        st.success(f"✅ {created} slot(s) created.")
                    if invalid:
                        st.warning("Invalid time slot(s): " + ", ".join(invalid))

    # AVAILABILITY
    with tabs[2]:
        st.markdown("### 📊 Slot Availability")
        restaurants = list_restaurants()
        if not restaurants:
            st.info("Create a restaurant first.")
        else:
            restaurant_names = [row[0] for row in restaurants]
            selected_restaurant = st.selectbox(
                "Restaurant",
                restaurant_names,
                key="availability_restaurant",
            )

            availability_date = st.date_input("Date", key="availability_date",)
            rows = list_slots(selected_restaurant, availability_date,)
            if rows:
                data = []
                for (slot_time, total_tables, booked_tables,) in rows:
                    available = max(0, total_tables - booked_tables,)
                    status = ("FULL"
                        if available == 0
                        else "AVAILABLE"
                    )

                    data.append([slot_time,total_tables, booked_tables, available, status,])

                df = pd.DataFrame(data, columns=["Time","Total Tables", "Booked Tables","Available Tables",
                        "Status",],)

                st.dataframe(df, use_container_width=True, hide_index=True,)
            else:
                st.info("No time slots configured for this date.")

    # BOOKINGS
    with tabs[3]:
        st.markdown("### 📋 All Booking Requests")
        rows = list_all_bookings()
        if not rows:
            st.info("No booking requests yet.")
        else:
            for row in rows:
                (
                    booking_id,
                    restaurant,
                    booking_date,
                    booking_time,
                    guests,
                    name,
                    contact,
                    tables_reserved,
                    status,
                    created,
                ) = row

                st.markdown(
                    f"""
                    <div class="card">

                        <div class="badge">
                            Booking #{booking_id}
                        </div>

                        <h4>{restaurant}</h4>

                        <div class="small">
                            📅 {booking_date}
                            • 🕒 {booking_time}
                            • 👥 {guests} guests
                        </div>

                        <p>
                            <b>Customer:</b> {name}
                        </p>

                        <p>
                            <b>Contact:</b> {contact}
                        </p>

                        <p>
                            <b>Tables Reserved:</b>
                            {tables_reserved}
                        </p>

                        <p>
                            <b>Status:</b> {status}
                        </p>

                        <div class="small">
                            Created: {created}
                        </div>

                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # PENDING ACTIONS
                if status == "PENDING":
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Confirm Booking",key=f"confirm_{booking_id}",use_container_width=True,):
                            ok, msg = update_booking_status(booking_id, "CONFIRMED",)

                            if ok:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)

                    with col2:
                        if st.button(
                            "❌ Reject Booking",
                            key=f"reject_{booking_id}",
                            use_container_width=True,
                        ):

                            ok, msg = update_booking_status(booking_id,"REJECTED",)
                            if ok:
                                st.warning(msg)
                                st.rerun()
                            else:
                                st.error(msg)