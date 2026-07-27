package tv.childtv.app

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.leanback.widget.Presenter

/** Cards for the top "Channels" selector row. */
class ChannelCardPresenter : Presenter() {

    class ChannelViewHolder(view: View) : Presenter.ViewHolder(view) {
        val title: TextView = view.findViewById(R.id.channel_title)
    }

    override fun onCreateViewHolder(parent: ViewGroup): ViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.card_channel, parent, false)
        return ChannelViewHolder(view)
    }

    override fun onBindViewHolder(viewHolder: ViewHolder, item: Any) {
        val channel = item as ChannelItem
        val holder = viewHolder as ChannelViewHolder
        holder.title.text = channel.title
        holder.view.alpha = if (channel.enabled) 1f else 0.5f
    }

    override fun onUnbindViewHolder(viewHolder: ViewHolder) {
        // nothing to clean up
    }
}
