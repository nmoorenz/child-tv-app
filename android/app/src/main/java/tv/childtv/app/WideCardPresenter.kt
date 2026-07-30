package tv.childtv.app

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageView
import android.widget.TextView
import androidx.leanback.widget.Presenter
import com.bumptech.glide.Glide

/** Wider card used by grid-layout channels (e.g. Kid Crew): 2-line title + date. */
class WideCardPresenter : Presenter() {

    class WideViewHolder(view: View) : Presenter.ViewHolder(view) {
        val image: ImageView = view.findViewById(R.id.card_image)
        val title: TextView = view.findViewById(R.id.card_title)
        val subtitle: TextView = view.findViewById(R.id.card_subtitle)
        val progressFill: View = view.findViewById(R.id.progress_fill)
    }

    override fun onCreateViewHolder(parent: ViewGroup): ViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.card_wide, parent, false)
        return WideViewHolder(view)
    }

    override fun onBindViewHolder(viewHolder: ViewHolder, item: Any) {
        val ep = item as Episode
        val holder = viewHolder as WideViewHolder
        val context = holder.view.context

        holder.title.text = ep.name
        holder.subtitle.text = ep.subtitle ?: ""

        val thumb = ep.thumbnail
            ?: ep.videoId?.let { "https://i.ytimg.com/vi/$it/hqdefault.jpg" }
        Glide.with(context)
            .load(thumb)
            .placeholder(R.drawable.default_thumb)
            .error(R.drawable.default_thumb)
            .centerCrop()
            .into(holder.image)

        val fraction = ep.videoId?.let { ProgressStore.fraction(context, it) } ?: 0f
        val density = context.resources.displayMetrics.density
        val fillPx = (fraction * CARD_WIDTH_DP * density).toInt()
        val lp = holder.progressFill.layoutParams
        lp.width = fillPx
        holder.progressFill.layoutParams = lp
        holder.progressFill.visibility = if (fraction > 0f) View.VISIBLE else View.GONE
    }

    override fun onUnbindViewHolder(viewHolder: ViewHolder) {
        val holder = viewHolder as WideViewHolder
        Glide.with(holder.view.context).clear(holder.image)
    }

    companion object {
        private const val CARD_WIDTH_DP = 380
    }
}
